import type { LocalNetworkConfig } from "./local-network.js";
import { assertLocalDeploymentTargets } from "./local-network.js";
import {
  AttemptExistsError,
  DeploymentBlocked,
  assertSubmissionDurable,
  createDeployAttempt,
  decideDeployRecovery,
  readDeployAttempt,
  withSubmissionIntent,
  writeDeployAttempt,
  type DeployAttemptRecord,
  type IdentifierObservation,
} from "./deploy-attempt.js";

export type DeploymentSettlement<T> = {
  result?: T;
  primaryError?: unknown;
  stopError?: unknown;
};

/**
 * Await the deployment attempt to settle, then stop the wallet.
 * A stop failure is returned separately and does not replace a primary error
 * or a successful result.
 */
export async function settleDeployment<T>(options: {
  work: () => Promise<T>;
  stopWallet?: () => Promise<void>;
}): Promise<DeploymentSettlement<T>> {
  let result: T | undefined;
  let primaryError: unknown;
  let stopError: unknown;
  try {
    result = await options.work();
  } catch (error) {
    primaryError = error;
  } finally {
    if (options.stopWallet) {
      try {
        await options.stopWallet();
      } catch (error) {
        stopError = error;
      }
    }
  }
  return { result, primaryError, stopError };
}

export type DeploymentDependencies = {
  network: LocalNetworkConfig;
  attemptPath: string;
  now: () => string;
  walletAddress: string;
  nodeUrls: Pick<DeployAttemptRecord, "nodeUrl" | "indexerUrl" | "indexerWsUrl" | "proofServerUrl">;
  construct: () => Promise<{ contractAddress: string; signingKey: unknown }>;
  readSigningKey: (contractAddress: string) => Promise<unknown>;
  persistSigningKey: (contractAddress: string, signingKey: unknown) => Promise<void>;
  proveAndBalance: () => Promise<string[]>;
  submit: (watchId: string) => Promise<string>;
  watch: (watchId: string) => Promise<IdentifierObservation>;
};

/**
 * One deployment attempt. An existing record blocks every callback that could
 * construct or submit. The final transaction id is written and read back
 * before submit is called.
 */
export async function executeDeploymentAttempt(
  deps: DeploymentDependencies,
): Promise<DeployAttemptRecord> {
  assertLocalDeploymentTargets(deps.network);
  const existing = readDeployAttempt(deps.attemptPath);
  if (existing) throw new DeploymentBlocked(existing);

  const constructedAt = deps.now();
  const built = await deps.construct();
  let constructed: DeployAttemptRecord;
  try {
    constructed = createDeployAttempt(deps.attemptPath, {
      version: 1,
      state: "constructed",
      networkId: "undeployed",
      nodeUrl: deps.nodeUrls.nodeUrl,
      indexerUrl: deps.nodeUrls.indexerUrl,
      indexerWsUrl: deps.nodeUrls.indexerWsUrl,
      proofServerUrl: deps.nodeUrls.proofServerUrl,
      walletAddress: deps.walletAddress,
      contractAddress: built.contractAddress,
      identifiers: [],
      watchId: null,
      createdAt: constructedAt,
      updatedAt: constructedAt,
    });
  } catch (error) {
    if (error instanceof AttemptExistsError) {
      const raced = readDeployAttempt(deps.attemptPath);
      if (raced) throw new DeploymentBlocked(raced);
    }
    throw error;
  }

  const identifiers = await deps.proveAndBalance();
  const intended = withSubmissionIntent(constructed, identifiers, deps.now());
  const durable = writeDeployAttempt(deps.attemptPath, intended);
  const watchId = assertSubmissionDurable(durable, identifiers);

  const storedKey = await deps.readSigningKey(built.contractAddress);
  if (storedKey != null) {
    throw new Error("refusing to overwrite an existing contract signing key");
  }
  await deps.persistSigningKey(built.contractAddress, built.signingKey);
  const stillDurable = readDeployAttempt(deps.attemptPath);
  if (!stillDurable) {
    throw new Error("refusing to submit before the attempt record is durable");
  }
  assertSubmissionDurable(stillDurable, identifiers);

  const submittedId = await deps.submit(watchId);

  const submittedIdentifiers = durable.identifiers.includes(submittedId)
    ? durable.identifiers
    : [...durable.identifiers, submittedId];
  const submitted = writeDeployAttempt(deps.attemptPath, {
    ...durable,
    state: "submitted",
    identifiers: submittedIdentifiers,
    watchId: submittedIdentifiers.includes(submittedId) ? submittedId : durable.watchId,
    updatedAt: deps.now(),
  });

  const observation = await deps.watch(submitted.watchId ?? watchId);
  const decision = decideDeployRecovery(submitted, [observation]);
  if (decision.kind === "blocked") return submitted;
  return writeDeployAttempt(deps.attemptPath, {
    ...decision.record,
    updatedAt: deps.now(),
  });
}
