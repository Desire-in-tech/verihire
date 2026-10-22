# VeriHire

VeriHire matches a PDF CV to a job, then asks a Midnight service for an eligibility proof. The public site can run without that service. When Midnight is not configured, verification is reported as unavailable. The API does not invent a transaction id, a proof id, or a successful verification.

```text
browser (Vercel) → Backend API (Render) → AI extraction (Render)
                                       └→ Midnight service (not publicly deployed)
```

The Midnight contract, wallet client, proof flow, and tests stay in `contract/` and `midnight_service/`. They are not started by the public web deployment.

## What works where

| Capability | Local undeployed stack | Public web deployment |
| --- | --- | --- |
| Employer signup, login, and scoped results | Yes, with the API running | Yes, after the API is deployed and `DATABASE_URL` points at Postgres |
| PDF upload, keyword or Claude extraction, match score | Yes | Yes, after the AI service and shared `AI_SERVICE_TOKEN` are set |
| Midnight eligibility proof | Yes on the preserved local demo. Tag `verihire-demo-success-2026-10-22` points at commit `22a2a2a18e438f0d8da542395305cab732846bc2` | No. Leave `MIDNIGHT_SERVICE_URL` empty. Status is `not_configured` |
| Durable employer rows across a restart | Yes, when `DATABASE_URL` or a SQLite file on a persistent disk is set | Only when `DATABASE_URL` is set. Render's free disk is ephemeral |

This repository does not claim that end-to-end Midnight verification works on public Preprod. That has not been deployed or tested. The local demo was one accepted contract deployment and one job-004 verification on an undeployed network. Do not redeploy that contract and do not retry that upload.

## Deployment URLs

No public frontend, API, or AI URL is recorded here yet. Hosting was not completed in the security-and-persistence change because provider credentials and a free database slot were not both available. Fill these in only after a deployment responds:

- Frontend (Vercel): not deployed from this change
- API (Render), `GET /health`: not deployed from this change
- AI service (Render), `GET /health`: not deployed from this change

`NEXT_PUBLIC_API_URL` is baked into the frontend at build time. Set it to the API origin and rebuild after the API URL exists.

## Local development

Use a separate terminal per process. Do not point `MIDNIGHT_SERVICE_URL` at a public proof server.

```bash
pip install -r Backend/requirements.txt
pip install -r ai_service/requirements.txt

# API — copy Backend/.env.example to Backend/.env first, or export the variables
uvicorn Backend.main:app --reload --port 8000

# AI — copy ai_service/.env.example to ai_service/.env
# From the repository root the import path is the package, not app.main:
uvicorn ai_service.app.main:app --reload --port 8001

cd frontend
npm ci
# copy frontend/.env.example to frontend/.env.local
npm run dev
```

The profile upload accepts PDF files only. The browser checks the extension, and the API checks the `%PDF-` header, a 2 MB limit, and extractable text. Scanned PDFs are rejected.

Create an employer at `/signup`. The session token is kept in `sessionStorage` under `verihire.employerToken`. Employer pages send it as `Authorization: Bearer`. Candidate upload uses `GET /api/jobs`, which returns job id, title, and company only.

Seed jobs are loaded only when `EMPLOYER_BOOTSTRAP_EMAIL` and `EMPLOYER_BOOTSTRAP_PASSWORD` (at least 12 characters) are set. They belong to that one bootstrap employer. A password already stored for that email is not overwritten on the next boot. Signup does not copy the seed jobs onto the new employer.

## Environment variables

Set these in the shell, a local untracked `.env`, or the host's environment settings. Do not commit real values.

| Name | Where | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | API | Postgres connection string. Unset uses SQLite at `VERIHIRE_DB_PATH` or `Backend/.local/verihire.sqlite` |
| `CORS_ORIGINS` | API | Comma-separated frontend origins. `*` is rejected |
| `EMPLOYER_BOOTSTRAP_EMAIL` | API | Optional owner for the seed catalog |
| `EMPLOYER_BOOTSTRAP_PASSWORD` | API | Optional bootstrap password, minimum 12 characters |
| `EMPLOYER_BOOTSTRAP_NAME` | API | Optional display name for that employer |
| `AI_SERVICE_URL` | API | AI base URL, default `http://localhost:8001` |
| `AI_SERVICE_TOKEN` | API and AI | Shared bearer secret. If unset, the API does not send CV text and the AI service returns 503 |
| `AI_SERVICE_TIMEOUT` | API | Seconds, default 60 |
| `MIDNIGHT_SERVICE_URL` | API | Midnight HTTP service. Leave empty on the public site |
| `MIDNIGHT_SERVICE_TIMEOUT` | API | Seconds, default 60. This is shorter than a Preprod genesis sync |
| `ENABLE_API_DOCS` | API | `true` exposes `/docs`. Default is off |
| `ANTHROPIC_API_KEY` | AI | Optional. Unset uses the keyword fallback |
| `ANTHROPIC_MODEL` | AI | Claude model id when the key is set |
| `NEXT_PUBLIC_API_URL` | Frontend | Public API origin. This is not a secret, but it is fixed at build time |

Midnight wallet variables (`WALLET_SEED`, `MIDNIGHT_STORAGE_PASSWORD`, Blockfrost project URLs) stay in the Midnight service environment. They are not required for the web deployment and must not be committed. See `midnight_service/.env.example` for names only.

## Vercel, Render, and Supabase

Frontend root is `frontend/`. On Vercel use install `npm ci`, build `npm run build`, and leave the output directory empty so Next.js uses its default. Set `NEXT_PUBLIC_API_URL` in the project environment before the build. The Vercel Hobby plan is for non-commercial personal use. This change does not enable a paid Vercel feature.

`render.yaml` describes two free web services, `verihire-api` and `verihire-ai`. It does not describe the frontend or Midnight. Render's free web instance has 512 MB RAM, spins down after 15 minutes, and has an ephemeral disk. A workspace gets 750 free instance hours per month. Two services awake all month exceed that allowance, so expect spin-down. Free web services cannot receive private-network traffic, so the API calls the AI service over HTTPS with `AI_SERVICE_TOKEN`. Do not add a persistent disk (`$0.25/GB`) or a paid instance. Without a card, Render suspends a workspace that exceeds the free bandwidth or build allowance instead of charging. Do not add a payment method to get past that.

Render free Postgres expires 30 days after creation and is then deleted after a grace period. It is not the store used by this change. The API speaks Postgres through `DATABASE_URL` when that variable starts with `postgres`.

Supabase is the intended durable store. The free organization `Desire-in-tech` already has two active projects, which is the free allowance. This change does not create, pause, or reuse a project. Until a free Postgres URL is supplied, rows on Render's local SQLite file disappear when the free instance restarts or spins down. `/health` reports `persistence` as `sqlite` or `postgres` and does not include a connection string.

## AI behavior

`POST /extract` and `POST /parse-job` require the bearer token. `GET /health` is public and reports `ai_enabled` and `auth_configured`. It does not return the Anthropic key or the service token.

With `ANTHROPIC_API_KEY` set, extraction calls Claude and falls back to keywords if that call fails. Without the key, extraction is the offline keyword list in `ai_service/app/extraction.py`. That fallback can miss skills, invent nothing beyond the listed keywords, and is not a judgment of a candidate. The summary field says when the fallback ran. CV text is not written to the API's HTTP error responses.

## Midnight status

Midnight is implemented and preserved. Public Preprod infrastructure is not deployed.

Preserved on the tagged local demo:

- Compact contract and compiled artifacts under `contract/` and `midnight_service/`
- Wallet, proof generation, transaction submission, and verification code
- The deploy guard that only accepts the local undeployed network and refuses a second deployment while an attempt record exists
- Outcome rules: `applicant_verified` is true only when status is `verified` and `eligible` is true. An unknown outcome that already has a proof id stays unknown and must not be resubmitted automatically. An empty `MIDNIGHT_SERVICE_URL` returns `not_configured` and no proof id

The Python client also refuses these hosts before any HTTP call, because they are not an approved prover for this project: `proof-server.preprod.midnight.network` and `lace-proof-pub.preprod`, `preview`, and `mainnet` under `midnight.network`. A blocked host returns `unavailable` and does not create a proof id.

The candidate dashboard cards, including the Pending card, are sample copy. The employer page at `/employer` is the live results view, and it asks for a sign-in before it calls the API.

### Later Preprod deployment

Do this only as a separate change, with an approved host and a new wallet. Do not reuse the local undeployed deployment, and do not send witnesses to the undocumented public prover.

1. Run proof server image `midnightntwrk/proof-server:8.1.3` on loopback (`http://127.0.0.1:6300`) on a host that can also hold the signing wallet. Render free disk, serverless, and the Windows PC are not that host. A card-free remote VM was not available; Oracle Always Free was the candidate and signup stopped at the card check.
2. Change the Midnight service so an explicit `preprod` configuration is allowed. Today the deploy path is hard-coded to `undeployed`. Keep refusing an automatic second deploy.
3. Raise the one-shot wallet sync wait above the current `120_000` ms and the Python client timeout above the current 60 seconds. A first Preprod sync from genesis can take more than an hour, and Blockfrost lag can take several minutes. Do not add a retry of an unknown submission.
4. Create a new Blockfrost Preprod project. Set the node and indexer URLs from the environment. The documented shapes are `https://rpc.midnight-preprod.blockfrost.io?project_id=` and `https://midnight-preprod.blockfrost.io/api/v0?project_id=`. Treat the project id as a secret. Do not use the retired `rpc.preprod.midnight.network` or `indexer.preprod.midnight.network` hosts.
5. Create a new wallet, fund it from the Preprod faucet, and register DUST. Keep the seed and storage password in the host environment.
6. Deploy the contract once, confirm the transaction, and set `CONTRACT_ADDRESS` from that deployment.
7. Set the API's `MIDNIGHT_SERVICE_URL` to the Midnight HTTP service, not to the proof server. Confirm `GET /midnight/health` before any upload. Submit one test upload. If the outcome is unknown, stop.

## Security limitations

These fixes are not a production security review.

- Employer routes require a bearer token. The employer id is taken from that server-side session. A client-supplied employer id is ignored.
- Passwords are hashed with PBKDF2-SHA256. Session tokens are stored as SHA-256 hashes and expire after 7 days. There is no MFA, email verification, password reset, or session revocation list.
- Signup returns 409 when the email already exists, which reveals that an account is present.
- The browser keeps the token in `sessionStorage` because the frontend and API are different sites. Any script that runs in the frontend origin can read it.
- Candidate upload is an unauthenticated write. It is limited to 2 MB PDFs and must name an active job. There is no rate limit and no malware scan. The response omits CV text and extracted credentials. The text remains in the database for the owning employer and is not returned by employer routes.
- Employer matching results omit reasoning and missing-requirement text.
- `/docs` is off unless `ENABLE_API_DOCS=true`.
- CORS allows only the configured origins and does not send cookies.
- Unexpected server errors use a generic message. That is not a guarantee that every dependency is silent.
- Seed job titles are public. Job descriptions and criteria require the owning employer.
- The candidate overview still shows sample application cards so the existing layout remains. Those numbers are not verification results.

## Tests

```bash
python -m unittest Backend.tests.test_access_control Backend.tests.test_midnight_blocked_host Backend.tests.test_employer_results Backend.tests.test_midnight_outcomes Backend.tests.test_midnight_connectivity
python -m unittest Backend.tests.test_applicant_verified_flag
cd frontend && npm run lint && npx tsc --noEmit
```

Run the applicant-flag test in its own process. It can install an import stub when FastAPI is absent. Midnight wallet, proof, and transaction commands are not part of these checks.

From `midnight_service`, the preserved suite is `./node_modules/.bin/tsc` and `./node_modules/.bin/tsx --test`. Do not run a proof or a deployment as a test.

## Troubleshooting

- Upload says extraction is unavailable: set the same `AI_SERVICE_TOKEN` on the API and the AI service, and set `AI_SERVICE_URL` to the AI origin. An empty token is a refusal, not a call.
- Employer results stay empty: sign in as the employer that owns the job. Another employer's upload is a 404, not an empty claim of success.
- `/health` shows `persistence: sqlite` on Render: `DATABASE_URL` is unset, so a restart drops rows.
- Verification says not configured: `MIDNIGHT_SERVICE_URL` is empty. That is the expected public behavior.
- Verification says unavailable immediately: the configured host is blocked, or the Midnight service could not be reached. No proof was recorded.
- CORS failure in the browser: set `CORS_ORIGINS` to the exact Vercel origin, without a trailing wildcard, and redeploy the API.
- Frontend still calls localhost: rebuild it after changing `NEXT_PUBLIC_API_URL`.
- Two Render services will sleep: open `/health` on each after idle time. The first request wakes a free instance.
