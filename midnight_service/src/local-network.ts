/**
 * Local undeployed endpoints.
 *
 * Networks guide, environment reference:
 * https://docs.midnight.network/guides/networks-and-environments
 * network id `undeployed`, node `http://localhost:9944`,
 * indexer `http://localhost:8088/api/v4/graphql`,
 * indexer websocket `ws://localhost:8088/api/v4/graphql/ws`,
 * proof server `http://localhost:6300`.
 *
 * A blank variable falls back to those defaults. Set the variable to use
 * another network. Public Preprod is Blockfrost plus a project token, not
 * the retired Midnight-hosted Preprod hosts.
 */

export type MidnightNetworkId = "undeployed" | "preprod";

export type LocalNetworkConfig = {
  networkId: MidnightNetworkId;
  nodeUrl: string;
  indexerUrl: string;
  indexerWsUrl: string;
  proofServerUrl: string;
};

export const LOCAL_UNDEPLOYED: LocalNetworkConfig = {
  networkId: "undeployed",
  nodeUrl: "http://localhost:9944",
  indexerUrl: "http://localhost:8088/api/v4/graphql",
  indexerWsUrl: "ws://localhost:8088/api/v4/graphql/ws",
  proofServerUrl: "http://localhost:6300",
};

function orDefault(value: string | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

export function readLocalNetworkConfig(
  env: Record<string, string | undefined>,
): LocalNetworkConfig {
  const networkId = orDefault(env.NETWORK_ID, LOCAL_UNDEPLOYED.networkId);
  if (networkId !== "undeployed" && networkId !== "preprod") {
    throw new Error(`NETWORK_ID must be undeployed or preprod, received ${networkId}`);
  }
  return {
    networkId,
    nodeUrl: orDefault(env.NODE_URL, LOCAL_UNDEPLOYED.nodeUrl),
    indexerUrl: orDefault(env.INDEXER_URL, LOCAL_UNDEPLOYED.indexerUrl),
    indexerWsUrl: orDefault(env.INDEXER_WS_URL, LOCAL_UNDEPLOYED.indexerWsUrl),
    proofServerUrl: orDefault(env.PROOF_SERVER_URL, LOCAL_UNDEPLOYED.proofServerUrl),
  };
}

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1"]);

function assertLoopbackUrl(
  value: string,
  label: string,
  protocol: "http:" | "ws:",
  port: string,
  pathname: string,
): void {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${label} is not a deployment URL`);
  }
  if (url.protocol !== protocol || url.username || url.password || url.search || url.hash) {
    throw new Error(`${label} is not an approved local deployment endpoint`);
  }
  if (!LOOPBACK_HOSTS.has(url.hostname) || url.port !== port || url.pathname !== pathname) {
    throw new Error(`${label} is not an approved local deployment endpoint`);
  }
}

/**
 * Deploy-only guard. readLocalNetworkConfig stays permissive for the service.
 * This rejects preprod and any endpoint that is not the local undeployed
 * loopback node, indexer, or proof server.
 */
export function assertLocalDeploymentTargets(config: LocalNetworkConfig): void {
  if (config.networkId !== "undeployed") {
    throw new Error("deployment is restricted to NETWORK_ID=undeployed");
  }
  assertLoopbackUrl(config.nodeUrl, "NODE_URL", "http:", "9944", "/");
  assertLoopbackUrl(config.indexerUrl, "INDEXER_URL", "http:", "8088", "/api/v4/graphql");
  assertLoopbackUrl(config.indexerWsUrl, "INDEXER_WS_URL", "ws:", "8088", "/api/v4/graphql/ws");
  assertLoopbackUrl(config.proofServerUrl, "PROOF_SERVER_URL", "http:", "6300", "/");
}
