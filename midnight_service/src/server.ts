/**
 * What this file does
 * --------------------
 * The HTTP surface the Python backend talks to (via backend/app/midnight_client.py)
 * once MIDNIGHT_SERVICE_URL is actually set. Two endpoints:
 *
 *   GET  /health   - liveness + whether a contract address is configured
 *   POST /prove     - runs the proveEligibility circuit against the
 *                     deployed contract with the given private inputs,
 *                     and returns a ProofResult shaped exactly like
 *                     backend/app/models.py's ProofResult (same field
 *                     names - see SCHEMA_CONTRACT.md).
 *
 * /prove checks the explicit local network and wallet sync before it joins
 * the contract or builds a transaction. /health does not submit anything.
 *
 * Same honesty note as the rest of this folder: this is written against
 * the real Midnight docs/SDK (findDeployedContract + callTx, per
 * https://docs.midnight.network/tutorials/bboard/bboard-api-implementation)
 * but has not been run against a live network from this environment - you
 * will need a compiled contract, a running proof server, node+indexer RPC
 * access, and a funded wallet before this actually produces a real proof.
 * Until then, keep MIDNIGHT_SERVICE_URL unset on the Python side. The
 * backend reports not_configured and does not invent a proof.
 */

import 'dotenv/config';
import express from 'express';
import { existsSync } from 'node:fs';
import { findDeployedContract } from '@midnight-ntwrk/midnight-js-contracts';
import { CompiledContract } from '@midnight-ntwrk/midnight-js-protocol/compact-js';
import { readEligibility } from './eligibility.js';
import { readLocalNetworkConfig, type LocalNetworkConfig } from './local-network.js';
import { registerProveRoute } from './prove-route.js';
import { buildProviders, readWalletSeed } from './providers.js';

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 7000);
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS ?? '';
const COMPILED_CONTRACT_DIR = new URL('../managed/verihire', import.meta.url).pathname;

type BuiltProviders = Awaited<ReturnType<typeof buildProviders>>;

type BuiltContract = {
  callTx: {
    proveEligibility: (
      resultKey: Uint8Array,
      pythonYears: bigint,
      hasPostgresql: boolean,
      hasAwsCert: boolean,
      hasBachelorsOrEquivalent: boolean,
      requiredPythonYears: bigint,
      requirePostgresql: boolean,
      requireAwsCert: boolean,
      requireBachelors: boolean,
    ) => Promise<{ public: { txId?: string | null; blockHeight?: number | null } }>;
  };
};

let providersPromise: Promise<BuiltProviders> | null = null;
let activeProviders: BuiltProviders | null = null;
let contractPromise: Promise<BuiltContract> | null = null;
let connectedNetwork: LocalNetworkConfig | null = null;

function sameNetwork(left: LocalNetworkConfig, right: LocalNetworkConfig): boolean {
  return (
    left.networkId === right.networkId &&
    left.nodeUrl === right.nodeUrl &&
    left.indexerUrl === right.indexerUrl &&
    left.indexerWsUrl === right.indexerWsUrl &&
    left.proofServerUrl === right.proofServerUrl
  );
}

async function loadProviders(network: LocalNetworkConfig): Promise<BuiltProviders> {
  if (connectedNetwork && !sameNetwork(connectedNetwork, network)) {
    throw new Error('refusing to change the proof network');
  }
  if (!providersPromise) {
    connectedNetwork = network;
    providersPromise = buildProviders({
      indexerUrl: network.indexerUrl,
      indexerWsUrl: network.indexerWsUrl,
      proofServerUrl: network.proofServerUrl,
      nodeUrl: network.nodeUrl,
      compiledContractDir: COMPILED_CONTRACT_DIR,
      walletAddress: process.env.WALLET_ADDRESS ?? '',
      networkId: network.networkId,
      walletSeed: readWalletSeed(),
      storagePassword: process.env.MIDNIGHT_STORAGE_PASSWORD ?? '',
    }).catch((error: unknown) => {
      providersPromise = null;
      connectedNetwork = null;
      throw error;
    });
  }
  return providersPromise;
}

async function joinDeployedContract(providers: BuiltProviders): Promise<BuiltContract> {
  const compiledContractModule = new URL(
    '../managed/verihire/contract/index.js',
    import.meta.url,
  ).href;
  const contractModule = await import(compiledContractModule);
  // No witnesses: node-server-wallet guide uses withVacantWitnesses.
  const compiledContract = CompiledContract.withCompiledFileAssets(
    CompiledContract.withVacantWitnesses(
      CompiledContract.make('Verihire', contractModule.Contract),
    ),
    COMPILED_CONTRACT_DIR,
  );

  return findDeployedContract(providers as never, {
    contractAddress: CONTRACT_ADDRESS,
    compiledContract: compiledContract as never,
  }) as unknown as Promise<BuiltContract>;
}

app.get('/health', (_req, res) => {
  const network = readLocalNetworkConfig(process.env);
  res.json({
    status: 'ok',
    contract_configured: Boolean(CONTRACT_ADDRESS),
    compiled_contract_configured: existsSync(
      new URL('../managed/verihire/contract/index.js', import.meta.url),
    ),
    wallet_configured: Boolean(process.env.WALLET_SEED && process.env.MIDNIGHT_STORAGE_PASSWORD),
    network: network.networkId,
  });
});

registerProveRoute(app, {
  env: process.env,
  connect: async (network) => {
    const providers = await loadProviders(network);
    activeProviders = providers;
    return {
      // whenWalletReady is assertWalletReady(waitForSyncedState).
      awaitWalletReady: () => providers.whenWalletReady(),
    };
  },
  joinContract: () => {
    const providers = activeProviders;
    if (!providers) {
      throw new Error('wallet connection was not started');
    }
    if (!contractPromise) {
      contractPromise = joinDeployedContract(providers).catch((error: unknown) => {
        contractPromise = null;
        throw error;
      });
    }
    return contractPromise;
  },
  readOutcome: async (_providers, resultKeyBytes) => {
    const providers = activeProviders;
    if (!providers) {
      throw new Error('wallet connection was not started');
    }
    const ledgerState = await providers.publicDataProvider
      .queryContractState(CONTRACT_ADDRESS)
      .then((state: any) => state?.data);
    const compiledContractModule = new URL(
      '../managed/verihire/contract/index.js',
      import.meta.url,
    ).href;
    const { ledger: toLedger } = await import(compiledContractModule);
    const publicLedger = toLedger(ledgerState);
    return readEligibility(publicLedger.eligibilityResults, resultKeyBytes);
  },
});

app.listen(PORT, () => {
  console.log(`VeriHire Midnight service listening on :${PORT}`);
  if (!CONTRACT_ADDRESS) {
    console.warn('CONTRACT_ADDRESS is not set - /prove will fail until you deploy the contract and set it.');
  }
});
