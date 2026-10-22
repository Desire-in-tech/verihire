import assert from "node:assert/strict";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import test from "node:test";
import type { Express } from "express";
import {
  LOCAL_UNDEPLOYED,
  assertLocalDeploymentTargets,
  readLocalNetworkConfig,
  requireExplicitLocalProofConfig,
} from "../src/local-network.ts";
import { createProveApp, type ProveOutcome, type ProveRouteDependencies } from "../src/prove-route.ts";
import { assertWalletReady } from "../src/wallet-ready.ts";

const EXPLICIT_LOCAL = {
  NETWORK_ID: "undeployed",
  NODE_URL: "http://127.0.0.1:9944",
  INDEXER_URL: "http://127.0.0.1:8088/api/v4/graphql",
  INDEXER_WS_URL: "ws://127.0.0.1:8088/api/v4/graphql/ws",
  PROOF_SERVER_URL: "http://127.0.0.1:6300",
  CONTRACT_ADDRESS: "test-contract",
};

function proofBody() {
  return {
    result_key: "11".repeat(32),
    python_years: 4,
    has_postgresql: true,
    has_aws_cert: false,
    has_bachelors_or_equivalent: true,
    required_python_years: 3,
    require_postgresql: true,
    require_aws_cert: false,
    require_bachelors: true,
  };
}

async function postProve(app: Express, body: unknown) {
  const server = createServer(app);
  await new Promise<void>((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve());
  });
  const { port } = server.address() as AddressInfo;
  try {
    const response = await fetch(`http://127.0.0.1:${port}/prove`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    return { status: response.status, body: await response.json() };
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }
}

function routeHarness(options: {
  env: Record<string, string | undefined>;
  awaitWalletReady?: () => Promise<void>;
  submit?: () => Promise<{ public: { txId?: string | null; blockHeight?: number | null } }>;
  readOutcome?: () => Promise<ProveOutcome>;
}) {
  const order: string[] = [];
  const networks: Array<{ nodeUrl: string; networkId: string }> = [];
  const deps: ProveRouteDependencies = {
    env: options.env,
    connect: async (network) => {
      order.push("connect");
      networks.push({ nodeUrl: network.nodeUrl, networkId: network.networkId });
      return {
        awaitWalletReady:
          options.awaitWalletReady ??
          (() => assertWalletReady(async () => {
            order.push("ready");
            return { isSynced: true };
          })),
      };
    },
    joinContract: async () => {
      order.push("join");
      return {
        callTx: {
          proveEligibility: async () => {
            order.push("submit");
            if (options.submit) return options.submit();
            return { public: { txId: "tx-once", blockHeight: 7 } };
          },
        },
      };
    },
    readOutcome: async () => {
      order.push("read");
      if (options.readOutcome) return options.readOutcome();
      return { verification_status: "verified", eligible: true, message: "ok" };
    },
  };
  return { app: createProveApp(deps), order, networks };
}

test("deployment defaults remain available while proof config rejects blanks", () => {
  assert.deepEqual(readLocalNetworkConfig({}), LOCAL_UNDEPLOYED);
  assert.deepEqual(
    readLocalNetworkConfig({ NETWORK_ID: "  ", NODE_URL: "" }),
    LOCAL_UNDEPLOYED,
  );
  assert.doesNotThrow(() => assertLocalDeploymentTargets(LOCAL_UNDEPLOYED));
  assert.throws(() => requireExplicitLocalProofConfig({}), /NETWORK_ID must be set explicitly/);
  assert.throws(
    () =>
      requireExplicitLocalProofConfig({
        NETWORK_ID: "preprod",
        NODE_URL: "http://127.0.0.1:9944",
        INDEXER_URL: "http://127.0.0.1:8088/api/v4/graphql",
        INDEXER_WS_URL: "ws://127.0.0.1:8088/api/v4/graphql/ws",
        PROOF_SERVER_URL: "http://127.0.0.1:6300",
      }),
    /proof submission is restricted to NETWORK_ID=undeployed/,
  );
  assert.throws(
    () =>
      requireExplicitLocalProofConfig({
        NETWORK_ID: " ",
        NODE_URL: " ",
        INDEXER_URL: "\t",
        INDEXER_WS_URL: "",
        PROOF_SERVER_URL: "  ",
      }),
    /must be set explicitly/,
  );
});

test("POST /prove rejects missing, blank, malformed, and non-local networks before connect", async () => {
  const cases: Array<{ name: string; env: Record<string, string | undefined> }> = [
    { name: "missing", env: { CONTRACT_ADDRESS: "test-contract" } },
    {
      name: "blank",
      env: {
        NETWORK_ID: " ",
        NODE_URL: "",
        INDEXER_URL: "\t",
        INDEXER_WS_URL: " ",
        PROOF_SERVER_URL: "",
        CONTRACT_ADDRESS: "test-contract",
      },
    },
    {
      name: "missing node",
      env: {
        NETWORK_ID: "undeployed",
        INDEXER_URL: EXPLICIT_LOCAL.INDEXER_URL,
        INDEXER_WS_URL: EXPLICIT_LOCAL.INDEXER_WS_URL,
        PROOF_SERVER_URL: EXPLICIT_LOCAL.PROOF_SERVER_URL,
        CONTRACT_ADDRESS: "test-contract",
      },
    },
    { name: "malformed url", env: { ...EXPLICIT_LOCAL, NODE_URL: "not a url" } },
    { name: "chain name is not the network id", env: { ...EXPLICIT_LOCAL, NETWORK_ID: "undeployed1" } },
    { name: "preprod", env: { ...EXPLICIT_LOCAL, NETWORK_ID: "preprod" } },
    {
      name: "public node",
      env: { ...EXPLICIT_LOCAL, NODE_URL: "https://rpc.preprod.midnight.network" },
    },
    {
      name: "wrong proof port",
      env: { ...EXPLICIT_LOCAL, PROOF_SERVER_URL: "http://127.0.0.1:6301" },
    },
    {
      name: "unspecified address",
      env: { ...EXPLICIT_LOCAL, NODE_URL: "http://0.0.0.0:9944" },
    },
    {
      name: "missing contract",
      env: {
        NETWORK_ID: EXPLICIT_LOCAL.NETWORK_ID,
        NODE_URL: EXPLICIT_LOCAL.NODE_URL,
        INDEXER_URL: EXPLICIT_LOCAL.INDEXER_URL,
        INDEXER_WS_URL: EXPLICIT_LOCAL.INDEXER_WS_URL,
        PROOF_SERVER_URL: EXPLICIT_LOCAL.PROOF_SERVER_URL,
      },
    },
  ];

  for (const entry of cases) {
    const { app, order } = routeHarness({ env: entry.env });
    const response = await postProve(app, proofBody());
    assert.equal(response.status, 502, entry.name);
    assert.equal(response.body.proof_id, null, entry.name);
    assert.deepEqual(order, [], entry.name);
  }
});

test("POST /prove waits for a synced wallet before join and submission", async () => {
  const { app, order } = routeHarness({
    env: EXPLICIT_LOCAL,
    awaitWalletReady: () =>
      assertWalletReady(async () => {
        order.push("ready");
        return { isSynced: false };
      }),
  });
  const response = await postProve(app, proofBody());
  assert.equal(response.status, 502);
  assert.match(String(response.body.message), /wallet synchronization did not complete/);
  assert.deepEqual(order, ["connect", "ready"]);
});

test("an explicit local configuration submits once and does not retry a failure", async () => {
  const succeeded = routeHarness({ env: EXPLICIT_LOCAL });
  const ok = await postProve(succeeded.app, proofBody());
  assert.equal(ok.status, 200);
  assert.equal(ok.body.proof_id, "tx-once");
  assert.equal(ok.body.eligible, true);
  assert.deepEqual(succeeded.order, ["connect", "ready", "join", "submit", "read"]);
  assert.equal(succeeded.networks[0]?.nodeUrl, "http://127.0.0.1:9944");
  assert.equal(succeeded.order.filter((step) => step === "submit").length, 1);

  const failed = routeHarness({
    env: EXPLICIT_LOCAL,
    submit: async () => {
      throw new Error("submit failed");
    },
  });
  const error = await postProve(failed.app, proofBody());
  assert.equal(error.status, 502);
  assert.equal(error.body.verification_status, "failed");
  assert.equal(error.body.proof_id, null);
  assert.equal(error.body.block_height, null);
  assert.deepEqual(failed.order, ["connect", "ready", "join", "submit"]);
  assert.equal(failed.order.filter((step) => step === "submit").length, 1);
});

test("an outcome read failure after submission keeps the transaction id and does not retry", async () => {
  const { app, order } = routeHarness({
    env: EXPLICIT_LOCAL,
    submit: async () => ({ public: { txId: "tx-submitted", blockHeight: 9 } }),
    readOutcome: async () => {
      throw new Error("ledger read failed");
    },
  });
  const response = await postProve(app, proofBody());
  assert.equal(response.status, 502);
  assert.equal(response.body.verification_status, "unknown");
  assert.equal(response.body.eligible, null);
  assert.equal(response.body.proof_id, "tx-submitted");
  assert.equal(response.body.block_height, 9);
  assert.match(String(response.body.message), /submitted/i);
  assert.match(String(response.body.message), /pending and unknown/i);
  assert.match(String(response.body.message), /Do not resubmit it automatically/);
  assert.deepEqual(order, ["connect", "ready", "join", "submit", "read"]);
  assert.equal(order.filter((step) => step === "submit").length, 1);
});

test("POST /prove does not fall back to another explicit local network", async () => {
  const env = { ...EXPLICIT_LOCAL };
  const { app, order, networks } = routeHarness({ env });
  const first = await postProve(app, proofBody());
  assert.equal(first.status, 200);
  env.NODE_URL = "http://localhost:9944";
  env.INDEXER_URL = "http://localhost:8088/api/v4/graphql";
  env.INDEXER_WS_URL = "ws://localhost:8088/api/v4/graphql/ws";
  env.PROOF_SERVER_URL = "http://localhost:6300";
  const second = await postProve(app, proofBody());
  assert.equal(second.status, 502);
  assert.match(String(second.body.message), /refusing to change the proof network/);
  assert.deepEqual(networks.map((network) => network.nodeUrl), ["http://127.0.0.1:9944"]);
  assert.equal(order.filter((step) => step === "submit").length, 1);
});
