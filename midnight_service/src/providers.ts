/**
 * What this file does
 * --------------------
 * Builds the `providers` object that every other Midnight SDK call in this
 * service needs (deploying the contract, calling a circuit on it). This
 * wiring is copied from the pattern shown in Midnight's own "deploy an
 * app" guide (https://docs.midnight.network/guides/deploy-mn-app) using
 * the real npm packages this project depends on - it is NOT something we
 * were able to compile or run in this environment (no Midnight node,
 * indexer, or proof server reachable here), so treat it as a strong
 * starting point to debug against your actual local devnet, not a
 * guaranteed-working file.
 *
 * The one piece intentionally left as a TODO is the wallet/signing
 * provider - a real one needs to sign transactions with an actual funded
 * testnet wallet (e.g. via @midnight-ntwrk/wallet or a browser Lace wallet
 * connection), which is specific to how your team wants to hold that
 * wallet's key material. Everything else here only needs the URLs in
 * your .env file.
 */

import { levelPrivateStateProvider } from '@midnight-ntwrk/midnight-js-level-private-state-provider';
import { indexerPublicDataProvider } from '@midnight-ntwrk/midnight-js-indexer-public-data-provider';
import { NodeZkConfigProvider } from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import { httpClientProofProvider } from '@midnight-ntwrk/midnight-js-http-client-proof-provider';

export type VerihireCircuitId = 'proveEligibility' | 'checkResult';

export function buildProviders(env: {
  indexerUrl: string;
  indexerWsUrl: string;
  proofServerUrl: string;
  compiledContractDir: string; // path to the `managed/verihire` output of `compact compile`
  walletAddress: string;
}) {
  const privateStateProvider = levelPrivateStateProvider({
    privateStateStoreName: 'verihire-private-state',
    signingKeyStoreName: 'verihire-signing-keys',
    // Hackathon-only: a real deployment should source this from a proper
    // secret store, not a hardcoded string.
    privateStoragePasswordProvider: () => 'verihire-hackathon-demo',
    accountId: env.walletAddress,
  });

  const publicDataProvider = indexerPublicDataProvider(env.indexerUrl, env.indexerWsUrl);

  const zkConfigProvider = new NodeZkConfigProvider<VerihireCircuitId>(env.compiledContractDir);

  const proofProvider = httpClientProofProvider(env.proofServerUrl, zkConfigProvider);

  // TODO: wire up a real wallet/midnight provider here. It must implement
  // the WalletProvider + MidnightProvider interfaces from
  // @midnight-ntwrk/midnight-js-types and sign transactions with a funded
  // testnet wallet. See https://docs.midnight.network for the current
  // recommended approach (a programmatic wallet vs. a browser Lace
  // connection) - this differs enough by use case that we didn't want to
  // guess at your team's choice here.
  const walletAndMidnightProvider = undefined as unknown;

  return {
    privateStateProvider,
    publicDataProvider,
    zkConfigProvider,
    proofProvider,
    walletProvider: walletAndMidnightProvider,
    midnightProvider: walletAndMidnightProvider,
  };
}
