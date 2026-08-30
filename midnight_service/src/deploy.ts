/**
 * What this file does
 * --------------------
 * One-time script: deploys the compiled verihire.compact contract to
 * whichever Midnight network your providers point at (local devnet or
 * testnet), and prints the resulting contract address - copy that into
 * CONTRACT_ADDRESS in your .env so server.ts knows where to call circuits.
 *
 * Run with: npm run deploy-contract
 * (after `compact compile ../contract/verihire.compact managed/verihire`
 * has produced the compiled contract artifacts this script imports)
 *
 * Same honesty note as providers.ts: this follows the documented pattern
 * from https://docs.midnight.network/guides/deploy-mn-app but has not
 * been run against a real network from this environment.
 */

import 'dotenv/config';
import { deployContract } from '@midnight-ntwrk/midnight-js-contracts';
import { buildProviders } from './providers.js';

async function main() {
  const providers = buildProviders({
    indexerUrl: process.env.INDEXER_URL ?? '',
    indexerWsUrl: process.env.INDEXER_WS_URL ?? '',
    proofServerUrl: process.env.PROOF_SERVER_URL ?? 'http://localhost:6300',
    compiledContractDir: new URL('../managed/verihire', import.meta.url).pathname,
    walletAddress: process.env.WALLET_ADDRESS ?? '',
  });

  // `compiledContract` is whatever `compact compile` generated for
  // verihire.compact - typically a TypeScript module under managed/verihire
  // that this import path should point at once the contract is compiled.
  // @ts-expect-error - path only exists after running `compact compile`
  const { contract: compiledContract } = await import('../managed/verihire/contract/index.cjs');

  const deployed = await deployContract(providers as never, {
    compiledContract,
    privateStateId: 'verihirePrivateState',
    initialPrivateState: {},
  });

  console.log('Deployed VeriHire contract at address:');
  console.log(deployed.deployTxData.public.contractAddress);
}

main().catch((err) => {
  console.error('Deployment failed:', err);
  process.exit(1);
});
