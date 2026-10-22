# VeriHire deployment lifecycle checkpoint

This document preserves the current development state so work can continue later. It is not approval to deploy.

## Checkpoint

- Repository: `Desire-in-tech/verihire`
- Remote: `https://github.com/Desire-in-tech/verihire`
- Established development branch: `integration`. This checkpoint does not update `integration` or `main`.
- Local `integration` when the checkpoint branch was created: `66cbf81e71b76855f9f8f1177fa72e909f378d11` (`fix: handle Midnight eligibility outcomes safely`). That commit was local only. `origin/integration` remained `c8df3313efd12314b6b72cce54627fcf804ec1c5`.
- Checkpoint branch: `checkpoint/verihire-deployment-lifecycle`
- Deployment lifecycle commit: `fd03d98c08014efea249d2a3df1139ef4da6104c`
- This handoff file is the child of that commit. Check out the branch tip; it contains both the lifecycle tree and this document.
- Branch URL: `https://github.com/Desire-in-tech/verihire/tree/checkpoint/verihire-deployment-lifecycle`
- Lifecycle commit URL: `https://github.com/Desire-in-tech/verihire/commit/fd03d98c08014efea249d2a3df1139ef4da6104c`

## What is already implemented

Steps 4.14b–4.14i are in `fd03d98`. Step 4.14k's transaction-id confirmation is in the commit that updates this document.

Deployment recovery files:

- `midnight_service/src/deploy.ts` — local undeployed deploy command. Refuses to start when an attempt record exists. Prints success only when the record state is `accepted`.
- `midnight_service/src/deploy-attempt.ts` — durable attempt record under `midnight_service/.local/`, exclusive create, fail-closed corrupt records, and the current reconciliation rule.
- `midnight_service/src/deploy-flow.ts` — construct, prove, balance, persist the post-balance transaction ids, persist the signing key, submit the same balanced transaction, then watch.
- `midnight_service/src/local-network.ts` — service network defaults, plus a deploy-only loopback `undeployed` guard.
- `midnight_service/src/providers.ts` — wallet provider wiring used by that flow, including separate reporting if wallet shutdown fails.
- `midnight_service/src/server.ts` — eligibility HTTP service. It does not serve `.local/` or start a deployment.
- `midnight_service/test/deploy-attempt.test.ts`
- `midnight_service/test/local-network.test.ts`
- `midnight_service/test/eligibility.test.ts` was already committed in `66cbf81` and still passes.

Related project changes included in the same checkpoint, outside the deploy-command patch:

- `.gitignore` ignores `midnight-level-db/`. `.local/` was already ignored.
- `midnight_service/.env.example` documents empty local undeployed defaults. It contains no seed or password.
- `midnight_service/Dockerfile` pins Compact `0.31.1` for the image compile.
- `midnight_service/package-lock.json` changed without a `package.json` change.
- `Backend/data/seed_jobs.json` and `Backend/tests/test_midnight_outcomes.py` extend the earlier Midnight outcome work.
- `frontend/components/cv-upload-form.tsx` is the uncommitted upload-form follow-up. The eligibility-label files were already in `66cbf81`.

## Safeguards in the current code

- The attempt record lives at `midnight_service/.local/verihire-deploy-attempt.json`, mode `0600`, and is gitignored. Any existing record blocks another deployment. Records are not deleted automatically.
- Creation is exclusive. Corrupt, partial, or unreadable records fail closed.
- The post-balance transaction identifiers are written and read back before the signing key is stored and before submission.
- An existing signing key is not overwritten.
- Prove or balance failure leaves a `constructed` record and does not store a key.
- Submission failure leaves `submission-intended`. An uncertain indexer result leaves the record blocked.
- Indexer `FAILURE` and `PARTIAL_SUCCESS` become `included-unsuccessful` and still block a new deployment.
- The deploy command checks loopback `undeployed` endpoints before it builds providers.
- Wallet stop failure is reported separately from the deployment result.
- Acceptance requires indexer status `SUCCESS` for a stored transaction id. That is the status the installed indexer client maps to `SucceedEntirely`. The ledger contract address captured at construction is kept and is not compared with indexer contract-address strings.

## Known limitations

- The ledger address string and the indexer contract-address string have not been shown to be the same encoding. Do not invent a prefix, length, or conversion.
- Confirmation means the stored transaction id was found with indexer status `SUCCESS`. It does not re-read `ContractDeploy.address` from the deserialized transaction. The saved ledger address remains the address to copy into `CONTRACT_ADDRESS`.
- A successful transaction id must not be used as permission to deploy again. `accepted` still blocks another deployment.
- A `constructed` record has no transaction id. It still blocks, and retiring it is a manual operator decision. The unproven transaction is not stored, so a later deploy would be a different contract.
- If the signing key is written and submission then fails or the process stops, the record stays `submission-intended`. The key is not deleted and the same unproven transaction cannot be resumed.
- `watchForTxData` has no timeout. The command's reconcile path uses one fetch and treats errors as unavailable.
- No contract deployment has been confirmed.

## Step 4.14j

The ledger-to-indexer address comparison is not verified. Installed comments disagree: the ledger type comment says a hex-encoded 35-byte contract address, while `assertIsContractAddress` and the Compact runtime checker require 32 bytes. The indexer schema types the address only as `HexEncoded`. No fixture shows both representations of one address, and no installed function is documented as converting one into the other. Do not guess a conversion.

## Step 4.14k

Implemented in the recovery decision, not by calling `deployContract`.

`decideDeployRecovery` accepts a `found` observation only when its identifier is one of the stored identifiers or `watchId` and its status is `SUCCESS`. The installed indexer client maps that status to `SucceedEntirely` in `toTxStatus`. `FAILURE` and `PARTIAL_SUCCESS` stay `included-unsuccessful`. Empty, pending, unknown, and unavailable observations stay blocked. A different indexer contract-address string does not block `SUCCESS` and does not replace the stored ledger address.

The post-submit watch still uses the transaction id. The one-shot reconcile query reads `transactionResult.status` and `identifiers` for that same id. Neither path converts a contract address.

Offline checks after this patch: `git diff --check` clean, `tsc --noEmit` exit 0, and 27 tests passed (`deploy-attempt`, `eligibility`, and `local-network`). No wallet was started and no transaction was submitted.

## Next step

Deployment is still not authorized. The next action is a separate explicit approval before any wallet start, proof, or submission. Do not repeat funding. Do not delete an attempt record to force another deployment.

## Do not do these without a new explicit approval

- Do not run the deploy command.
- Do not start or initialize a wallet.
- Do not construct, prove, balance, sign, or submit a transaction.
- Do not repeat funding. Local wallet funding was already performed once.
- Do not query the node or indexer as part of implementing the next patch unless that later task explicitly allows a read-only query.
- Do not edit `.env`, the funding marker, an existing attempt record, contract source, or compiled artifacts just to make a deploy succeed.
- Deployment remains unauthorized.
