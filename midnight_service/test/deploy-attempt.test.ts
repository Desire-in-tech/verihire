import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { LOCAL_UNDEPLOYED } from "../src/local-network.ts";
import {
  AttemptExistsError,
  DeploymentBlocked,
  acquireDeployLock,
  blocksNewDeployment,
  createDeployAttempt,
  decideDeployRecovery,
  observationFromTxQuery,
  readDeployAttempt,
  writeDeployAttempt,
  type DeployAttemptRecord,
  type IdentifierObservation,
} from "../src/deploy-attempt.ts";
import {
  executeDeploymentAttempt,
  settleDeployment,
  type DeploymentDependencies,
} from "../src/deploy-flow.ts";

const NETWORK_URLS = {
  nodeUrl: LOCAL_UNDEPLOYED.nodeUrl,
  indexerUrl: LOCAL_UNDEPLOYED.indexerUrl,
  indexerWsUrl: LOCAL_UNDEPLOYED.indexerWsUrl,
  proofServerUrl: LOCAL_UNDEPLOYED.proofServerUrl,
};

function record(overrides: Partial<DeployAttemptRecord> = {}): DeployAttemptRecord {
  return {
    version: 1,
    state: "submission-intended",
    networkId: "undeployed",
    ...NETWORK_URLS,
    walletAddress: "mn_addr_undeployed1example",
    contractAddress: "contract-address",
    identifiers: ["intent-id", "final-id"],
    watchId: "final-id",
    createdAt: "2026-10-21T00:00:00.000Z",
    updatedAt: "2026-10-21T00:00:00.000Z",
    ...overrides,
  };
}

function tempAttempt(): { directory: string; path: string; lockPath: string; cleanup: () => void } {
  const directory = mkdtempSync(join(tmpdir(), "verihire-deploy-attempt-"));
  return {
    directory,
    path: join(directory, "attempt.json"),
    lockPath: join(directory, "attempt.lock"),
    cleanup: () => rmSync(directory, { recursive: true, force: true }),
  };
}

function installRecord(path: string, next: DeployAttemptRecord): void {
  createDeployAttempt(path, {
    ...next,
    state: "constructed",
    identifiers: [],
    watchId: null,
  });
  if (next.state !== "constructed" || next.identifiers.length !== 0 || next.watchId !== null) {
    writeDeployAttempt(path, next);
  }
}

function deploymentDeps(
  path: string,
  overrides: Partial<DeploymentDependencies> = {},
): DeploymentDependencies {
  return {
    network: LOCAL_UNDEPLOYED,
    attemptPath: path,
    now: () => "2026-10-21T00:00:01.000Z",
    walletAddress: "mn_addr_undeployed1example",
    nodeUrls: NETWORK_URLS,
    construct: async () => ({
      contractAddress: "contract-address",
      signingKey: "signing-key-must-not-be-stored",
    }),
    readSigningKey: async () => null,
    persistSigningKey: async () => {},
    proveAndBalance: async () => ["intent-id", "final-id"],
    submit: async () => "final-id",
    watch: async (identifier) => ({
      kind: "found",
      identifier,
      status: "SUCCESS",
      contractAddresses: ["contract-address"],
    }),
    ...overrides,
  };
}

test("an unresolved attempt blocks every later deployment", () => {
  for (const state of [
    "constructed",
    "submission-intended",
    "submitted",
    "accepted",
    "included-unsuccessful",
  ] as const) {
    assert.equal(blocksNewDeployment(record({ state, identifiers: state === "constructed" ? [] : ["final-id"], watchId: state === "constructed" ? null : "final-id" })), true);
  }
  assert.equal(blocksNewDeployment(null), false);
});

test("an existing attempt does not construct or submit", async () => {
  const attempt = tempAttempt();
  let constructed = false;
  let submitted = false;
  try {
    installRecord(attempt.path, record());
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            construct: async () => {
              constructed = true;
              return { contractAddress: "other", signingKey: "secret" };
            },
            submit: async () => {
              submitted = true;
              return "final-id";
            },
          }),
        ),
      DeploymentBlocked,
    );
    assert.equal(constructed, false);
    assert.equal(submitted, false);
    assert.equal(readDeployAttempt(attempt.path)?.state, "submission-intended");
  } finally {
    attempt.cleanup();
  }
});

test("the final transaction id is durable before submission and before the signing key", async () => {
  const attempt = tempAttempt();
  let persistedState = "";
  let persistedWatchId = "";
  let signingKeyPersisted = false;
  try {
    const result = await executeDeploymentAttempt(
      deploymentDeps(attempt.path, {
        proveAndBalance: async () => {
          assert.equal(signingKeyPersisted, false);
          assert.equal(readDeployAttempt(attempt.path)?.state, "constructed");
          assert.equal(readDeployAttempt(attempt.path)?.identifiers.length, 0);
          return ["intent-id", "final-id"];
        },
        readSigningKey: async () => {
          const onDisk = readDeployAttempt(attempt.path);
          assert.equal(onDisk?.state, "submission-intended");
          assert.deepEqual(onDisk?.identifiers, ["intent-id", "final-id"]);
          return null;
        },
        persistSigningKey: async (address, signingKey) => {
          assert.equal(address, "contract-address");
          assert.equal(signingKey, "signing-key-must-not-be-stored");
          signingKeyPersisted = true;
          assert.equal(readDeployAttempt(attempt.path)?.state, "submission-intended");
        },
        submit: async (watchId) => {
          assert.equal(signingKeyPersisted, true);
          const onDisk = JSON.parse(readFileSync(attempt.path, "utf8")) as DeployAttemptRecord;
          persistedState = onDisk.state;
          persistedWatchId = onDisk.watchId ?? "";
          assert.equal(watchId, "final-id");
          assert.equal(onDisk.identifiers.at(-1), "final-id");
          assert.equal(JSON.stringify(onDisk).includes("signing-key"), false);
          return watchId;
        },
      }),
    );
    assert.equal(persistedState, "submission-intended");
    assert.equal(persistedWatchId, "final-id");
    assert.equal(result.state, "accepted");
    assert.equal(result.watchId, "final-id");
    const stored = JSON.parse(readFileSync(attempt.path, "utf8")) as Record<string, unknown>;
    for (const key of ["seed", "signingKey", "password", "unprovenTx"]) {
      assert.equal(Object.hasOwn(stored, key), false);
    }
  } finally {
    attempt.cleanup();
  }
});

test("a signing-key store failure does not submit and keeps the transaction id", async () => {
  const attempt = tempAttempt();
  let submitted = false;
  try {
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            persistSigningKey: async () => {
              throw new Error("signing key store failed");
            },
            submit: async () => {
              submitted = true;
              return "final-id";
            },
          }),
        ),
      /signing key store failed/,
    );
    assert.equal(submitted, false);
    assert.equal(readDeployAttempt(attempt.path)?.state, "submission-intended");
    assert.equal(readDeployAttempt(attempt.path)?.watchId, "final-id");
  } finally {
    attempt.cleanup();
  }
});

test("an existing signing key is not overwritten and blocks submission", async () => {
  const attempt = tempAttempt();
  let persisted = false;
  let submitted = false;
  try {
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            readSigningKey: async () => "already-stored",
            persistSigningKey: async () => {
              persisted = true;
            },
            submit: async () => {
              submitted = true;
              return "final-id";
            },
          }),
        ),
      /overwrite/,
    );
    assert.equal(persisted, false);
    assert.equal(submitted, false);
    assert.equal(readDeployAttempt(attempt.path)?.state, "submission-intended");
  } finally {
    attempt.cleanup();
  }
});

test("proving or balancing failure leaves a constructed record and does not store a key", async () => {
  const attempt = tempAttempt();
  let persisted = false;
  let submitted = false;
  try {
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            proveAndBalance: async () => {
              throw new Error("prove failed");
            },
            persistSigningKey: async () => {
              persisted = true;
            },
            submit: async () => {
              submitted = true;
              return "final-id";
            },
          }),
        ),
      /prove failed/,
    );
    assert.equal(persisted, false);
    assert.equal(submitted, false);
    assert.equal(readDeployAttempt(attempt.path)?.state, "constructed");
    assert.deepEqual(readDeployAttempt(attempt.path)?.identifiers, []);
  } finally {
    attempt.cleanup();
  }
});

test("submission failure stays submission-intended", async () => {
  const attempt = tempAttempt();
  let persisted = false;
  try {
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            persistSigningKey: async () => {
              persisted = true;
            },
            submit: async () => {
              throw new Error("submit failed");
            },
          }),
        ),
      /submit failed/,
    );
    assert.equal(persisted, true);
    const stored = readDeployAttempt(attempt.path);
    assert.equal(stored?.state, "submission-intended");
    assert.equal(stored?.watchId, "final-id");
    assert.equal(JSON.stringify(stored).includes("signing-key"), false);
  } finally {
    attempt.cleanup();
  }
});

test("an uncertain indexer response does not become accepted", async () => {
  const attempt = tempAttempt();
  try {
    const missed = await executeDeploymentAttempt(
      deploymentDeps(attempt.path, {
        watch: async () => ({ kind: "empty", identifier: "final-id" }),
      }),
    );
    assert.equal(missed.state, "submitted");
    assert.notEqual(missed.state, "accepted");

    const mismatch = await executeDeploymentAttempt(
      deploymentDeps(join(attempt.directory, "other.json"), {
        watch: async (identifier) => ({
          kind: "found",
          identifier,
          status: "SUCCESS",
          contractAddresses: ["other-contract"],
        }),
      }),
    );
    assert.equal(mismatch.state, "accepted");
    assert.equal(mismatch.contractAddress, "contract-address");
  } finally {
    attempt.cleanup();
  }
});

test("exclusive creation rejects a second attempt before it can submit", async () => {
  const attempt = tempAttempt();
  let submits = 0;
  try {
    const first = record({ state: "constructed", identifiers: [], watchId: null });
    createDeployAttempt(attempt.path, first);
    assert.throws(() => createDeployAttempt(attempt.path, first), AttemptExistsError);
    assert.throws(() => writeDeployAttempt(join(attempt.directory, "missing.json"), first), /missing record/);

    const results = await Promise.allSettled([
      executeDeploymentAttempt(
        deploymentDeps(attempt.lockPath, {
          submit: async () => {
            submits += 1;
            return "final-id";
          },
        }),
      ),
      executeDeploymentAttempt(
        deploymentDeps(attempt.lockPath, {
          submit: async () => {
            submits += 1;
            return "final-id";
          },
        }),
      ),
    ]);
    const fulfilled = results.filter((result) => result.status === "fulfilled");
    assert.equal(fulfilled.length, 1);
    assert.equal(submits, 1);
    assert.equal(readDeployAttempt(attempt.lockPath)?.contractAddress, "contract-address");
  } finally {
    attempt.cleanup();
  }
});

test("a second lock is rejected before a deployment callback", () => {
  const attempt = tempAttempt();
  try {
    acquireDeployLock(attempt.lockPath);
    assert.throws(() => acquireDeployLock(attempt.lockPath), (error: unknown) => {
      return error instanceof Error && "code" in error && error.code === "EEXIST";
    });
  } finally {
    attempt.cleanup();
  }
});

test("corrupt and unreadable records fail closed", async () => {
  const attempt = tempAttempt();
  let constructed = false;
  try {
    writeFileSync(attempt.path, "{");
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            construct: async () => {
              constructed = true;
              return { contractAddress: "contract-address", signingKey: "key" };
            },
          }),
        ),
      SyntaxError,
    );
    assert.equal(constructed, false);
    assert.throws(() => readDeployAttempt(attempt.path), SyntaxError);

    const directoryPath = join(attempt.directory, "not-a-file");
    mkdirSync(directoryPath);
    assert.throws(() => readDeployAttempt(directoryPath));
    await assert.rejects(() =>
      executeDeploymentAttempt(
        deploymentDeps(directoryPath, {
          construct: async () => {
            constructed = true;
            return { contractAddress: "contract-address", signingKey: "key" };
          },
        }),
      ),
    );
    assert.equal(constructed, false);
  } finally {
    attempt.cleanup();
  }
});

test("the network guard runs before construction", async () => {
  const attempt = tempAttempt();
  let constructed = false;
  try {
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            network: {
              ...LOCAL_UNDEPLOYED,
              networkId: "preprod",
            },
            construct: async () => {
              constructed = true;
              return { contractAddress: "contract-address", signingKey: "key" };
            },
          }),
        ),
      /undeployed/,
    );
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            network: {
              ...LOCAL_UNDEPLOYED,
              nodeUrl: "http://127.0.0.1:9945",
            },
            construct: async () => {
              constructed = true;
              return { contractAddress: "contract-address", signingKey: "key" };
            },
          }),
        ),
      /NODE_URL/,
    );
    assert.equal(constructed, false);
    assert.equal(readDeployAttempt(attempt.path), null);
  } finally {
    attempt.cleanup();
  }
});

test("an indexer miss leaves the attempt blocked", () => {
  const current = record();
  const decision = decideDeployRecovery(current, [
    { kind: "empty", identifier: "intent-id" },
    { kind: "unavailable", identifier: "final-id" },
  ]);
  assert.equal(decision.kind, "blocked");
  assert.equal(decision.record.state, "submission-intended");
  assert.deepEqual(decision.record, current);
});

test("acceptance requires the stored transaction id and keeps the ledger address", () => {
  const current = record();
  const accepted = decideDeployRecovery(current, [
    {
      kind: "found",
      identifier: "final-id",
      status: "SUCCESS",
      contractAddresses: ["contract-address"],
    },
  ]);
  assert.equal(accepted.kind, "accepted");
  assert.equal(accepted.record.state, "accepted");
  assert.equal(accepted.record.contractAddress, "contract-address");
  assert.equal(accepted.record.watchId, "final-id");
  assert.equal(blocksNewDeployment(accepted.record), true);

  const differentIndexerAddress = decideDeployRecovery(current, [
    {
      kind: "found",
      identifier: "final-id",
      status: "SUCCESS",
      contractAddresses: ["other-contract"],
    },
  ]);
  assert.equal(differentIndexerAddress.kind, "accepted");
  assert.equal(differentIndexerAddress.record.contractAddress, "contract-address");
  assert.equal(differentIndexerAddress.record.state, "accepted");

  const wrongId = decideDeployRecovery(current, [
    {
      kind: "found",
      identifier: "someone-else",
      status: "SUCCESS",
      contractAddresses: ["contract-address"],
    },
  ]);
  assert.equal(wrongId.kind, "blocked");
  assert.equal(wrongId.record, current);
});

test("pending, failed, and unknown confirmation stay fail-closed", () => {
  const current = record({ state: "submitted" });
  for (const observation of [
    { kind: "empty", identifier: "final-id" },
    { kind: "unavailable", identifier: "final-id" },
  ] as const) {
    const decision = decideDeployRecovery(current, [observation]);
    assert.equal(decision.kind, "blocked");
    assert.equal(decision.record, current);
  }

  const failed = decideDeployRecovery(current, [
    {
      kind: "found",
      identifier: "final-id",
      status: "FAILURE",
      contractAddresses: ["contract-address"],
    },
  ]);
  assert.equal(failed.kind, "included-unsuccessful");
  assert.equal(failed.record.contractAddress, "contract-address");
  assert.equal(blocksNewDeployment(failed.record), true);
});

test("an interrupted submission is not resubmitted when the transaction id succeeds", async () => {
  const attempt = tempAttempt();
  let constructed = false;
  let submitted = false;
  try {
    installRecord(attempt.path, record({ state: "submitted" }));
    await assert.rejects(
      () =>
        executeDeploymentAttempt(
          deploymentDeps(attempt.path, {
            construct: async () => {
              constructed = true;
              return { contractAddress: "other", signingKey: "secret" };
            },
            submit: async () => {
              submitted = true;
              return "new-id";
            },
          }),
        ),
      DeploymentBlocked,
    );
    assert.equal(constructed, false);
    assert.equal(submitted, false);

    const recovered = decideDeployRecovery(readDeployAttempt(attempt.path)!, [
      {
        kind: "found",
        identifier: "final-id",
        status: "SUCCESS",
        contractAddresses: [],
      },
    ]);
    assert.equal(recovered.kind, "accepted");
    assert.equal(recovered.record.contractAddress, "contract-address");
    assert.equal(recovered.record.identifiers.includes("final-id"), true);
    assert.equal(blocksNewDeployment(recovered.record), true);
    assert.equal(readDeployAttempt(attempt.path)?.state, "submitted");
  } finally {
    attempt.cleanup();
  }
});

test("a failed inclusion stays blocked and is not treated as absent", () => {
  const decision = decideDeployRecovery(record(), [
    {
      kind: "found",
      identifier: "final-id",
      status: "PARTIAL_SUCCESS",
      contractAddresses: ["contract-address"],
    } satisfies IdentifierObservation,
  ]);
  assert.equal(decision.kind, "included-unsuccessful");
  assert.equal(decision.record.state, "included-unsuccessful");
  assert.equal(blocksNewDeployment(decision.record), true);
});

test("indexer transaction payloads become observations without a wallet", () => {
  assert.deepEqual(
    observationFromTxQuery("final-id", {
      data: {
        transactions: [
          {
            identifiers: ["intent-id", "final-id"],
            transactionResult: { status: "SUCCESS" },
            contractActions: [{ address: "contract-address" }],
          },
        ],
      },
    }),
    {
      kind: "found",
      identifier: "final-id",
      status: "SUCCESS",
      contractAddresses: ["contract-address"],
    },
  );
  assert.equal(observationFromTxQuery("final-id", { data: { transactions: [] } }).kind, "empty");
  assert.equal(observationFromTxQuery("final-id", { errors: [{}] }).kind, "unavailable");
  for (const status of ["PENDING", "UNKNOWN", undefined]) {
    const observation = observationFromTxQuery("final-id", {
      data: {
        transactions: [
          {
            identifiers: ["final-id"],
            transactionResult: { status },
          },
        ],
      },
    });
    assert.equal(observation.kind, "unavailable");
  }
  const missingId = observationFromTxQuery("final-id", {
    data: {
      transactions: [
        {
          identifiers: ["someone-else"],
          transactionResult: { status: "SUCCESS" },
        },
      ],
    },
  });
  assert.equal(missingId.kind, "unavailable");
});

test("wallet stop failure keeps the deployment result and the primary error", async () => {
  const order: string[] = [];
  const succeeded = await settleDeployment({
    work: async () => {
      order.push("work");
      return { contractAddress: "contract-address" };
    },
    stopWallet: async () => {
      order.push("stop");
      throw new Error("stop broke");
    },
  });
  assert.deepEqual(order, ["work", "stop"]);
  assert.equal(succeeded.result?.contractAddress, "contract-address");
  assert.equal(succeeded.primaryError, undefined);
  assert.equal(succeeded.stopError instanceof Error && succeeded.stopError.message, "stop broke");

  const failed = await settleDeployment({
    work: async () => {
      throw new Error("deploy broke");
    },
    stopWallet: async () => {
      throw new Error("stop broke");
    },
  });
  assert.equal(failed.result, undefined);
  assert.equal(failed.primaryError instanceof Error && failed.primaryError.message, "deploy broke");
  assert.equal(failed.stopError instanceof Error && failed.stopError.message, "stop broke");
});
