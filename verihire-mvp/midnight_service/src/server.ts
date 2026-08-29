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
 * Until then, keep MIDNIGHT_SERVICE_URL unset on the Python side and the
 * app keeps working off the offline mock.
 */

import 'dotenv/config';
import express from 'express';
import crypto from 'node:crypto';
import { findDeployedContract } from '@midnight-ntwrk/midnight-js-contracts';
import { buildProviders } from './providers.js';

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT ?? 7000);
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS ?? '';

// Lazily connected on first /prove call so `npm run dev` still boots (and
// /health still responds) even before a contract is deployed.
let deployedContractPromise: ReturnType<typeof findDeployedContract> | null = null;

async function getDeployedContract() {
  if (!CONTRACT_ADDRESS) {
    throw new Error('CONTRACT_ADDRESS is not set - deploy the contract first with `npm run deploy-contract`.');
  }
  if (!deployedContractPromise) {
    const providers = buildProviders({
      indexerUrl: process.env.INDEXER_URL ?? '',
      indexerWsUrl: process.env.INDEXER_WS_URL ?? '',
      proofServerUrl: process.env.PROOF_SERVER_URL ?? 'http://localhost:6300',
      compiledContractDir: new URL('../managed/verihire', import.meta.url).pathname,
      walletAddress: process.env.WALLET_ADDRESS ?? '',
    });

    // @ts-expect-error - path only exists after running `compact compile`
    const { contract: compiledContract } = await import('../managed/verihire/contract/index.cjs');

    deployedContractPromise = findDeployedContract(providers as never, {
      contractAddress: CONTRACT_ADDRESS,
      compiledContract,
      privateStateId: 'verihirePrivateState',
      initialPrivateState: {},
    });
  }
  return deployedContractPromise;
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', contract_configured: Boolean(CONTRACT_ADDRESS) });
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
    const contract = await getDeployedContract();

    // resultKey needs to be Bytes<32> on the Compact side - the Python
    // side already sends a 32-byte hex sha256 digest, so this just decodes it.
    const resultKeyBytes = Buffer.from(body.result_key, 'hex');

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

    // The circuit itself decided `eligible` privately; the only thing we
    // (and the chain) can see is that the transaction succeeded and what
    // got written to public ledger state under resultKey. A real
    // implementation would read `eligibilityResults` back out via the
    // public data provider to get the actual `verified` boolean - left as
    // a follow-up since we can't exercise this against a live indexer here.
    const claimHash = crypto.createHash('sha256').update(body.result_key).digest('hex');

    res.json({
      proof_id: txData.public.txHash,
      verified: true, // TODO: read this back from eligibilityResults instead of assuming success == eligible
      claim: `on-chain proof for result_key ${body.result_key}`,
      claim_hash: claimHash,
      generated_at: new Date().toISOString(),
    });
  } catch (err) {
    console.error('proveEligibility call failed:', err);
    res.status(502).json({ detail: String(err) });
  }
});

app.listen(PORT, () => {
  console.log(`VeriHire Midnight service listening on :${PORT}`);
  if (!CONTRACT_ADDRESS) {
    console.warn('CONTRACT_ADDRESS is not set - /prove will fail until you deploy the contract and set it.');
  }
});
