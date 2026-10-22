/**
 * Deploy the compiled VeriHire contract to the local undeployed network.
 *
 * The command refuses to start when midnight_service/.local/verihire-deploy-attempt.json
 * exists. An indexer miss does not clear that record and does not start
 * another deployment. Success is printed only after the indexer reports the
 * stored transaction id and the same contract address string. Copy that
 * address into CONTRACT_ADDRESS by hand; this script does not edit .env.
 *
 * Run with: npm run deploy-contract
 */

import "dotenv/config";
import { existsSync } from "node:fs";
import { createUnprovenDeployTx } from "@midnight-ntwrk/midnight-js-contracts";
import { CompiledContract } from "@midnight-ntwrk/midnight-js-protocol/compact-js";
import { sampleSigningKey } from "@midnight-ntwrk/compact-runtime";
import {
  DEPLOY_ATTEMPT_PATH,
  DEPLOY_LOCAL_DIR,
  DEPLOY_LOCK_PATH,
  acquireDeployLock,
  decideDeployRecovery,
  ensureDeployDirectory,
  observationFromTxQuery,
  readDeployAttempt,
  releaseDeployLock,
  writeDeployAttempt,
  type DeployAttemptRecord,
  type IdentifierObservation,
} from "./deploy-attempt.js";
import { executeDeploymentAttempt, settleDeployment } from "./deploy-flow.js";
import { assertLocalDeploymentTargets, readLocalNetworkConfig } from "./local-network.js";
import { buildProviders, readWalletSeed } from "./providers.js";

function publicFailure(error: unknown): string {
  const name = error instanceof Error ? error.name : "Error";
  const message = error instanceof Error ? error.message : "";
  const redacted = message.replace(/\b[0-9a-fA-F]{32,}\b/g, "[redacted-hex]");
  return redacted ? `${name}: ${redacted}` : name;
}

const TX_QUERY = `query TX_ID_QUERY($offset: TransactionOffset!) {
  transactions(offset: $offset) {
    hash
    contractActions { address }
    ... on RegularTransaction {
      identifiers
      transactionResult { status }
    }
  }
}`;

async function queryIdentifier(indexerUrl: string, identifier: string): Promise<IdentifierObservation> {
  try {
    const response = await fetch(indexerUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        query: TX_QUERY,
        variables: { offset: { identifier } },
      }),
    });
    if (!response.ok) return { kind: "unavailable", identifier };
    return observationFromTxQuery(identifier, await response.json());
  } catch {
    return { kind: "unavailable", identifier };
  }
}

async function reconcile(record: DeployAttemptRecord): Promise<DeployAttemptRecord> {
  assertLocalDeploymentTargets({
    networkId: record.networkId,
    nodeUrl: record.nodeUrl,
    indexerUrl: record.indexerUrl,
    indexerWsUrl: record.indexerWsUrl,
    proofServerUrl: record.proofServerUrl,
  });
  if (record.identifiers.length === 0) return record;
  const observations: IdentifierObservation[] = [];
  for (const identifier of record.identifiers) {
    observations.push(await queryIdentifier(record.indexerUrl, identifier));
  }
  const decision = decideDeployRecovery(record, observations);
  if (decision.record.state === record.state && decision.record.watchId === record.watchId) {
    return record;
  }
  return writeDeployAttempt(DEPLOY_ATTEMPT_PATH, {
    ...decision.record,
    updatedAt: new Date().toISOString(),
  });
}

function reportRecord(record: DeployAttemptRecord): void {
  console.log(`deployment attempt ${record.state}`);
  console.log(record.contractAddress);
  if (record.watchId) console.log(record.watchId);
  if (record.state !== "accepted") {
    console.error("deployment attempt remains unresolved; not starting another deployment");
  }
}

async function main() {
  const network = readLocalNetworkConfig(process.env);
  assertLocalDeploymentTargets(network);
  ensureDeployDirectory(DEPLOY_LOCAL_DIR);

  const existing = readDeployAttempt(DEPLOY_ATTEMPT_PATH);
  if (existing) {
    if (existsSync(DEPLOY_LOCK_PATH)) {
      reportRecord(existing);
      process.exitCode = 2;
      return;
    }
    const resolved = await reconcile(existing);
    reportRecord(resolved);
    if (resolved.state !== "accepted") process.exitCode = 2;
    return;
  }

  let lockHeld = false;
  try {
    acquireDeployLock(DEPLOY_LOCK_PATH);
    lockHeld = true;
  } catch (error) {
    const code = error instanceof Error && "code" in error ? error.code : undefined;
    if (code === "EEXIST") {
      console.error("deployment lock is present; not starting a deployment");
      process.exitCode = 2;
      return;
    }
    throw error;
  }

  let stopWallet: (() => Promise<void>) | undefined;
  try {
    const raced = readDeployAttempt(DEPLOY_ATTEMPT_PATH);
    if (raced) {
      const resolved = await reconcile(raced);
      reportRecord(resolved);
      if (resolved.state !== "accepted") process.exitCode = 2;
      return;
    }

    const settlement = await settleDeployment({
      stopWallet: async () => {
        if (stopWallet) await stopWallet();
      },
      work: async () => {
        const compiledContractDir = new URL("../managed/verihire", import.meta.url).pathname;
        const providers = await buildProviders({
          indexerUrl: network.indexerUrl,
          indexerWsUrl: network.indexerWsUrl,
          proofServerUrl: network.proofServerUrl,
          compiledContractDir,
          walletAddress: process.env.WALLET_ADDRESS ?? "",
          nodeUrl: network.nodeUrl,
          networkId: network.networkId,
          walletSeed: readWalletSeed(),
          storagePassword: process.env.MIDNIGHT_STORAGE_PASSWORD ?? "",
        });
        stopWallet = providers.stopWallet;

        const contractModule = await import(
          new URL("../managed/verihire/contract/index.js", import.meta.url).href
        );
        const compiledContract = CompiledContract.withCompiledFileAssets(
          CompiledContract.withVacantWitnesses(
            CompiledContract.make("Verihire", contractModule.Contract),
          ),
          compiledContractDir,
        );

        let unprovenTx: unknown;
        let balancedTx: { identifiers(): string[] } | undefined;
        const record = await executeDeploymentAttempt({
          network,
          attemptPath: DEPLOY_ATTEMPT_PATH,
          now: () => new Date().toISOString(),
          walletAddress: providers.walletAddress,
          nodeUrls: network,
          construct: async () => {
            const unproven = await createUnprovenDeployTx(providers, {
              compiledContract: compiledContract as never,
              args: [],
              signingKey: sampleSigningKey(),
            });
            unprovenTx = unproven.private.unprovenTx;
            return {
              contractAddress: unproven.public.contractAddress,
              signingKey: unproven.private.signingKey,
            };
          },
          readSigningKey: (contractAddress) =>
            providers.privateStateProvider.getSigningKey(contractAddress),
          persistSigningKey: async (contractAddress, signingKey) => {
            const existingKey = await providers.privateStateProvider.getSigningKey(contractAddress);
            if (existingKey != null) {
              throw new Error("refusing to overwrite an existing contract signing key");
            }
            await providers.privateStateProvider.setSigningKey(contractAddress, signingKey as never);
          },
          proveAndBalance: async () => {
            if (!unprovenTx) throw new Error("deployment transaction was not constructed");
            const proven = await providers.proofProvider.proveTx(unprovenTx as never);
            balancedTx = await providers.walletProvider.balanceTx(proven);
            unprovenTx = undefined;
            return balancedTx.identifiers();
          },
          submit: async (watchId) => {
            if (!balancedTx) throw new Error("deployment transaction was not balanced");
            const identifiers = balancedTx.identifiers();
            if (identifiers[identifiers.length - 1] !== watchId) {
              throw new Error("refusing to submit a transaction whose final id changed");
            }
            const submittedId = await providers.midnightProvider.submitTx(balancedTx as never);
            if (!submittedId) throw new Error("deployment submission did not return a transaction id");
            return submittedId;
          },
          watch: async (watchId) => {
            await providers.publicDataProvider.watchForTxData(watchId);
            return queryIdentifier(network.indexerUrl, watchId);
          },
        });
        return record;
      },
    });

    if (settlement.result?.state === "accepted") {
      console.log("Deployed VeriHire contract at address:");
      console.log(settlement.result.contractAddress);
      if (settlement.result.watchId) console.log(settlement.result.watchId);
    } else if (settlement.result) {
      console.error(
        `deployment attempt ${settlement.result.state}; not starting another deployment`,
      );
      console.error(settlement.result.contractAddress);
      if (!settlement.primaryError) process.exitCode = 2;
    }
    if (settlement.primaryError) {
      console.error(`Deployment failed: ${publicFailure(settlement.primaryError)}`);
      process.exitCode = 1;
    }
    if (settlement.stopError) {
      console.error(`wallet stop failed: ${publicFailure(settlement.stopError)}`);
    }
  } finally {
    if (lockHeld) {
      try {
        releaseDeployLock(DEPLOY_LOCK_PATH);
      } catch {
        console.error("deployment lock could not be released");
      }
    }
  }
}

main().catch((error) => {
  console.error(`Deployment failed: ${publicFailure(error)}`);
  process.exitCode = 1;
});
