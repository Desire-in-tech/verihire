import {
  chmodSync,
  closeSync,
  constants,
  existsSync,
  fchmodSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeSync,
} from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Public deployment-recovery record.
 *
 * An indexer miss is not absence. This module never expires a record and
 * never authorizes a second deployment while a record exists. It never
 * deletes a record.
 */

const localDirectory = fileURLToPath(new URL("../.local/", import.meta.url));

export const DEPLOY_LOCAL_DIR = localDirectory;
export const DEPLOY_ATTEMPT_PATH = fileURLToPath(
  new URL("../.local/verihire-deploy-attempt.json", import.meta.url),
);
export const DEPLOY_LOCK_PATH = fileURLToPath(
  new URL("../.local/verihire-deploy.lock", import.meta.url),
);

export const DEPLOY_ATTEMPT_STATES = [
  "constructed",
  "submission-intended",
  "submitted",
  "accepted",
  "included-unsuccessful",
] as const;

export type DeployAttemptState = (typeof DEPLOY_ATTEMPT_STATES)[number];

export type DeployAttemptRecord = {
  version: 1;
  state: DeployAttemptState;
  networkId: "undeployed";
  nodeUrl: string;
  indexerUrl: string;
  indexerWsUrl: string;
  proofServerUrl: string;
  walletAddress: string;
  contractAddress: string;
  identifiers: string[];
  watchId: string | null;
  createdAt: string;
  updatedAt: string;
};

export type IdentifierObservation =
  | { kind: "empty"; identifier: string }
  | { kind: "unavailable"; identifier: string }
  | {
      kind: "found";
      identifier: string;
      status: "SUCCESS" | "FAILURE" | "PARTIAL_SUCCESS";
      contractAddresses: string[];
    };

export type RecoveryDecision = {
  kind: "blocked" | "accepted" | "included-unsuccessful";
  record: DeployAttemptRecord;
};

const FORBIDDEN_KEYS = new Set([
  "seed",
  "walletSeed",
  "signingKey",
  "privateKey",
  "password",
  "storagePassword",
  "mnemonic",
  "unprovenTx",
  "newCoins",
]);

export class DeploymentBlocked extends Error {
  readonly record: DeployAttemptRecord;

  constructor(record: DeployAttemptRecord) {
    super(`deployment attempt is unresolved in state ${record.state}`);
    this.name = "DeploymentBlocked";
    this.record = record;
  }
}

export class AttemptExistsError extends Error {
  constructor() {
    super("deployment attempt record already exists");
    this.name = "AttemptExistsError";
  }
}

function fsyncDirectory(filePath: string): void {
  const fd = openSync(dirname(filePath), "r");
  try {
    fsyncSync(fd);
  } finally {
    closeSync(fd);
  }
}

export function ensureDeployDirectory(directory: string): void {
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  chmodSync(directory, 0o700);
}

export function acquireDeployLock(lockPath: string): void {
  const fd = openSync(lockPath, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY, 0o600);
  try {
    writeSync(fd, `${process.pid}\n`);
    fsyncSync(fd);
  } finally {
    closeSync(fd);
  }
  fsyncDirectory(lockPath);
}

export function releaseDeployLock(lockPath: string): void {
  unlinkSync(lockPath);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string" && item.length > 0);
}

function assertPublicRecord(record: DeployAttemptRecord): void {
  const stack: unknown[] = [record];
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current || typeof current !== "object") continue;
    for (const [key, value] of Object.entries(current)) {
      if (FORBIDDEN_KEYS.has(key)) {
        throw new Error("deployment attempt record cannot store private material");
      }
      if (value && typeof value === "object") stack.push(value);
    }
  }
  if (record.version !== 1 || record.networkId !== "undeployed") {
    throw new Error("deployment attempt record is not a local undeployed attempt");
  }
  if (!DEPLOY_ATTEMPT_STATES.includes(record.state)) {
    throw new Error("deployment attempt record has an unknown state");
  }
  if (!record.contractAddress || !record.walletAddress) {
    throw new Error("deployment attempt record is missing a public address");
  }
  if (!isStringArray(record.identifiers)) {
    throw new Error("deployment attempt identifiers are not public strings");
  }
  if (record.watchId !== null && !record.identifiers.includes(record.watchId)) {
    throw new Error("deployment watch id is not one of the transaction identifiers");
  }
}

export function readDeployAttempt(path: string): DeployAttemptRecord | null {
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch (error) {
    if (error instanceof Error && "code" in error && error.code === "ENOENT") return null;
    throw error;
  }
  const parsed: unknown = JSON.parse(text);
  if (!parsed || typeof parsed !== "object") {
    throw new Error("deployment attempt record is unreadable");
  }
  const record = parsed as DeployAttemptRecord;
  assertPublicRecord(record);
  return record;
}

function durableBody(record: DeployAttemptRecord): string {
  assertPublicRecord(record);
  return JSON.stringify(record);
}

function readBack(path: string, record: DeployAttemptRecord): DeployAttemptRecord {
  const stored = readDeployAttempt(path);
  if (
    !stored ||
    stored.state !== record.state ||
    stored.contractAddress !== record.contractAddress ||
    stored.watchId !== record.watchId ||
    stored.identifiers.join("\n") !== record.identifiers.join("\n")
  ) {
    throw new Error("deployment attempt record was not durably stored");
  }
  return stored;
}

export function createDeployAttempt(path: string, record: DeployAttemptRecord): DeployAttemptRecord {
  if (record.state !== "constructed" || record.identifiers.length !== 0 || record.watchId !== null) {
    throw new Error("a new deployment attempt must start as constructed");
  }
  const body = durableBody(record);
  let fd: number;
  try {
    fd = openSync(path, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY, 0o600);
  } catch (error) {
    if (error instanceof Error && "code" in error && error.code === "EEXIST") {
      throw new AttemptExistsError();
    }
    throw error;
  }
  try {
    writeSync(fd, body);
    fchmodSync(fd, 0o600);
    fsyncSync(fd);
  } finally {
    closeSync(fd);
  }
  fsyncDirectory(path);
  return readBack(path, record);
}

export function writeDeployAttempt(path: string, record: DeployAttemptRecord): DeployAttemptRecord {
  if (!existsSync(path)) {
    throw new Error("refusing to create a deployment attempt by replacing a missing record");
  }
  const body = durableBody(record);
  const temporary = `${path}.tmp`;
  const fd = openSync(temporary, constants.O_CREAT | constants.O_TRUNC | constants.O_WRONLY, 0o600);
  try {
    writeSync(fd, body);
    fchmodSync(fd, 0o600);
    fsyncSync(fd);
  } catch (error) {
    try {
      unlinkSync(temporary);
    } catch {
      // The temporary file is not the attempt record.
    }
    throw error;
  } finally {
    closeSync(fd);
  }
  renameSync(temporary, path);
  fsyncDirectory(path);
  return readBack(path, record);
}

export function withSubmissionIntent(
  record: DeployAttemptRecord,
  identifiers: readonly string[],
  updatedAt: string,
): DeployAttemptRecord {
  if (record.state !== "constructed") {
    throw new Error("submission intent requires a constructed attempt");
  }
  if (identifiers.length === 0 || identifiers.some((id) => id.length === 0)) {
    throw new Error("balanced transaction did not expose a transaction identifier");
  }
  const watchId = identifiers[identifiers.length - 1]!;
  return writeShape({
    ...record,
    state: "submission-intended",
    identifiers: [...identifiers],
    watchId,
    updatedAt,
  });
}

function writeShape(record: DeployAttemptRecord): DeployAttemptRecord {
  assertPublicRecord(record);
  return record;
}

export function assertSubmissionDurable(
  persisted: DeployAttemptRecord,
  identifiers: readonly string[],
): string {
  const watchId = identifiers[identifiers.length - 1];
  if (
    persisted.state !== "submission-intended" ||
    !watchId ||
    persisted.watchId !== watchId ||
    persisted.identifiers.join("\n") !== identifiers.join("\n")
  ) {
    throw new Error("refusing to submit before the attempt record is durable");
  }
  return watchId;
}

function matchesAttempt(record: DeployAttemptRecord, identifier: string): boolean {
  return record.identifiers.includes(identifier) || record.watchId === identifier;
}

/**
 * Reconcile a stored attempt against indexer observations.
 *
 * Indexer status SUCCESS is the status the installed indexer client maps to
 * SucceedEntirely in `toTxStatus`. Acceptance uses that status and a stored
 * transaction id. The ledger contract address already on the record is kept
 * and is not compared with indexer contract-address strings.
 * Empty, pending, unknown, and unavailable queries leave the record unchanged
 * and blocked.
 */
export function decideDeployRecovery(
  record: DeployAttemptRecord,
  observations: readonly IdentifierObservation[],
): RecoveryDecision {
  const accepted = observations.find(
    (observation) =>
      observation.kind === "found" &&
      observation.status === "SUCCESS" &&
      matchesAttempt(record, observation.identifier),
  );
  if (accepted && accepted.kind === "found") {
    return {
      kind: "accepted",
      record: {
        ...record,
        state: "accepted",
        watchId: accepted.identifier,
      },
    };
  }

  const included = observations.find(
    (observation) =>
      observation.kind === "found" &&
      (observation.status === "FAILURE" || observation.status === "PARTIAL_SUCCESS") &&
      matchesAttempt(record, observation.identifier),
  );
  if (included) {
    return {
      kind: "included-unsuccessful",
      record: { ...record, state: "included-unsuccessful" },
    };
  }

  return { kind: "blocked", record };
}

export function blocksNewDeployment(record: DeployAttemptRecord | null): boolean {
  return record !== null;
}

type TxQueryTransaction = {
  identifiers?: unknown;
  transactionResult?: { status?: unknown };
  contractActions?: { address?: unknown }[];
};

export function observationFromTxQuery(identifier: string, body: unknown): IdentifierObservation {
  const unavailable = (): IdentifierObservation => ({ kind: "unavailable", identifier });
  if (!body || typeof body !== "object") return unavailable();
  const data = (body as { data?: unknown }).data;
  if (!data || typeof data !== "object") return unavailable();
  const transactions = (data as { transactions?: unknown }).transactions;
  if (!Array.isArray(transactions)) return unavailable();
  if (transactions.length === 0) return { kind: "empty", identifier };
  const transaction = transactions[0] as TxQueryTransaction;
  const status = transaction.transactionResult?.status;
  if (status !== "SUCCESS" && status !== "FAILURE" && status !== "PARTIAL_SUCCESS") {
    return unavailable();
  }
  if (!Array.isArray(transaction.identifiers) || !transaction.identifiers.includes(identifier)) {
    return unavailable();
  }
  const contractAddresses = Array.isArray(transaction.contractActions)
    ? transaction.contractActions
        .map((action) => action?.address)
        .filter((address): address is string => typeof address === "string" && address.length > 0)
    : [];
  return { kind: "found", identifier, status, contractAddresses };
}
