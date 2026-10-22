import assert from "node:assert/strict";
import test from "node:test";
import {
  LOCAL_UNDEPLOYED,
  assertLocalDeploymentTargets,
  readLocalNetworkConfig,
} from "../src/local-network.ts";

test("local defaults are the documented undeployed endpoints", () => {
  const config = readLocalNetworkConfig({});
  assert.equal(config.networkId, "undeployed");
  assert.equal(config.nodeUrl, "http://localhost:9944");
  assert.equal(config.indexerUrl, "http://localhost:8088/api/v4/graphql");
  assert.equal(config.indexerWsUrl, "ws://localhost:8088/api/v4/graphql/ws");
  assert.equal(config.proofServerUrl, "http://localhost:6300");
  assert.deepEqual(config, LOCAL_UNDEPLOYED);
  const serialized = JSON.stringify(config);
  assert.equal(serialized.includes("midnight.network"), false);
  assert.equal(serialized.includes("preprod"), false);
});

test("blank env values keep the local defaults and set values override them", () => {
  assert.deepEqual(readLocalNetworkConfig({ NETWORK_ID: "  ", NODE_URL: "" }), LOCAL_UNDEPLOYED);
  const overridden = readLocalNetworkConfig({
    NETWORK_ID: "preprod",
    NODE_URL: "http://127.0.0.1:9944",
    INDEXER_URL: "http://127.0.0.1:8088/api/v4/graphql",
    INDEXER_WS_URL: "ws://127.0.0.1:8088/api/v4/graphql/ws",
    PROOF_SERVER_URL: "http://127.0.0.1:6300",
  });
  assert.equal(overridden.networkId, "preprod");
  assert.equal(overridden.nodeUrl, "http://127.0.0.1:9944");
  assert.equal(overridden.proofServerUrl, "http://127.0.0.1:6300");
});

test("an unknown network id is rejected", () => {
  assert.throws(() => readLocalNetworkConfig({ NETWORK_ID: "preview" }), /NETWORK_ID/);
});

test("deployment allows only loopback undeployed endpoints", () => {
  assert.doesNotThrow(() => assertLocalDeploymentTargets(LOCAL_UNDEPLOYED));
  assert.doesNotThrow(() =>
    assertLocalDeploymentTargets({
      networkId: "undeployed",
      nodeUrl: "http://127.0.0.1:9944",
      indexerUrl: "http://127.0.0.1:8088/api/v4/graphql",
      indexerWsUrl: "ws://127.0.0.1:8088/api/v4/graphql/ws",
      proofServerUrl: "http://127.0.0.1:6300",
    }),
  );
  const preprod = readLocalNetworkConfig({
    NETWORK_ID: "preprod",
    NODE_URL: "http://127.0.0.1:9944",
    INDEXER_URL: "http://127.0.0.1:8088/api/v4/graphql",
    INDEXER_WS_URL: "ws://127.0.0.1:8088/api/v4/graphql/ws",
    PROOF_SERVER_URL: "http://127.0.0.1:6300",
  });
  assert.equal(preprod.networkId, "preprod");
  assert.throws(() => assertLocalDeploymentTargets(preprod), /undeployed/);
  assert.throws(
    () =>
      assertLocalDeploymentTargets({
        ...LOCAL_UNDEPLOYED,
        nodeUrl: "https://rpc.preprod.midnight.network",
      }),
    /NODE_URL/,
  );
  assert.throws(
    () =>
      assertLocalDeploymentTargets({
        ...LOCAL_UNDEPLOYED,
        indexerUrl: "http://127.0.0.1:8088/api/v3/graphql",
      }),
    /INDEXER_URL/,
  );
});
