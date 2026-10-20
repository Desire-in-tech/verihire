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
import { buildProviders, readWalletSeed } from './providers.js';

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 7000);
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS ?? '';
const NETWORK_ID = (process.env.NETWORK_ID ?? 'preprod') as 'preprod' | 'undeployed';
const COMPILED_CONTRACT_DIR = new URL('../managed/verihire', import.meta.url).pathname;

// Lazily connected on first /prove call so `npm run dev` still boots (and
// /health still responds) even before a contract is deployed.
let deployedContractPromise: Promise<any> | null = null;
let publicDataProvider: any = null;

async function getDeployedContract() {
  if (!CONTRACT_ADDRESS) {
    throw new Error('CONTRACT_ADDRESS is not set - deploy the contract first with `npm run deploy-contract`.');
  }
  if (!deployedContractPromise) {
    const providers = await buildProviders({
      indexerUrl: process.env.INDEXER_URL ?? '',
      indexerWsUrl: process.env.INDEXER_WS_URL ?? '',
      proofServerUrl: process.env.PROOF_SERVER_URL ?? 'http://localhost:6300',
      nodeUrl: process.env.NODE_URL ?? 'wss://rpc.preprod.midnight.network',
      compiledContractDir: COMPILED_CONTRACT_DIR,
      walletAddress: process.env.WALLET_ADDRESS ?? '',
      networkId: NETWORK_ID,
      walletSeed: readWalletSeed(),
      storagePassword: process.env.MIDNIGHT_STORAGE_PASSWORD ?? '',
    });
    publicDataProvider = providers.publicDataProvider;

    const compiledContractModule = new URL(
      '../managed/verihire/contract/index.js',
      import.meta.url,
    ).href;
    const contractModule = await import(compiledContractModule);
    const compiledContract = CompiledContract.make('Verihire', contractModule.Contract).pipe(
      CompiledContract.withCompiledFileAssets(COMPILED_CONTRACT_DIR),
    );

    deployedContractPromise = findDeployedContract(providers as never, {
      contractAddress: CONTRACT_ADDRESS,
      compiledContract: compiledContract as never,
    });
  }
  return deployedContractPromise;
}

app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    contract_configured: Boolean(CONTRACT_ADDRESS),
    compiled_contract_configured: existsSync(
      new URL('../managed/verihire/contract/index.js', import.meta.url),
    ),
    wallet_configured: Boolean(process.env.WALLET_SEED && process.env.MIDNIGHT_STORAGE_PASSWORD),
    network: NETWORK_ID,
  });
});

interface ProveRequestBody {
  result_key: string; // hex sha256 of "candidate_ref:job_id", computed by the Python backend
  python_years: number;
  has_postgresql: boolean;
  has_aws_cert: boolean;
  has_bachelors_or_equivalent: boolean;
  required_python_years: number;
  require_postgresql: boolean;
  require_aws_cert: boolean;
  require_bachelors: boolean;
}

app.post('/prove', async (req, res) => {
  const body = req.body as ProveRequestBody;

  try {
    if (
      !/^[0-9a-fA-F]{64}$/.test(body.result_key) ||
      !Number.isInteger(body.python_years) ||
      body.python_years < 0 ||
      !Number.isInteger(body.required_python_years) ||
      body.required_python_years < 0 ||
      typeof body.has_postgresql !== 'boolean' ||
      typeof body.has_aws_cert !== 'boolean' ||
      typeof body.has_bachelors_or_equivalent !== 'boolean' ||
      typeof body.require_postgresql !== 'boolean' ||
      typeof body.require_aws_cert !== 'boolean' ||
      typeof body.require_bachelors !== 'boolean'
    ) {
      return res.status(400).json({
        verification_status: 'failed',
        eligible: null,
        unsupported_criteria: [],
        proof_id: null,
        block_height: null,
        message: 'Invalid proof request',
      });
    }

    const contract = await getDeployedContract();

    // resultKey needs to be Bytes<32> on the Compact side - the Python
    // side already sends a 32-byte hex sha256 digest, so this just decodes it.
    const resultKeyBytes = Uint8Array.from(Buffer.from(body.result_key, 'hex'));

    const txData = await contract.callTx.proveEligibility(
      resultKeyBytes,
      BigInt(body.python_years),
      body.has_postgresql,
      body.has_aws_cert,
      body.has_bachelors_or_equivalent,
      BigInt(body.required_python_years),
      body.require_postgresql,
      body.require_aws_cert,
      body.require_bachelors,
    );

    const ledgerState = await publicDataProvider
      .queryContractState(CONTRACT_ADDRESS)
      .then((state: any) => state?.data);
    const compiledContractModule = new URL(
      '../managed/verihire/contract/index.js',
      import.meta.url,
    ).href;
    const { ledger: toLedger } = await import(compiledContractModule);
    const publicLedger = toLedger(ledgerState);
    const outcome = readEligibility(publicLedger.eligibilityResults, resultKeyBytes);

    res.json({
      verification_status: outcome.verification_status,
      eligible: outcome.eligible,
      unsupported_criteria: [],
      proof_id: txData.public.txId ?? null,
      block_height: txData.public.blockHeight ?? null,
      message: outcome.message,
    });
  } catch (err) {
    console.error('proveEligibility call failed:', err);
    res.status(502).json({
      verification_status: 'failed',
      eligible: null,
      unsupported_criteria: [],
      proof_id: null,
      block_height: null,
      message: String(err),
    });
  }
});

app.listen(PORT, () => {
  console.log(`VeriHire Midnight service listening on :${PORT}`);
  if (!CONTRACT_ADDRESS) {
    console.warn('CONTRACT_ADDRESS is not set - /prove will fail until you deploy the contract and set it.');
  }
});
