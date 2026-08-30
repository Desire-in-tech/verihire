# VeriHire

VeriHire is a privacy-aware hiring demo with four service boundaries:

```text
frontend → Backend API → AI extraction
                       └→ Midnight eligibility proof (optional until configured)
```

The project intentionally keeps the hackathon-friendly in-memory store and
seed jobs. It does not add a database or a Replit-specific deployment layer.

## Repository layout

- `frontend/` — Next.js candidate and employer UI
- `Backend/` — FastAPI upload, extraction, matching, and privacy-safe employer API
- `ai_service/` — structured CV extraction with an explicit offline keyword fallback
- `contract/` — Compact eligibility circuit
- `midnight_service/` — Node/TypeScript Midnight.js provider and HTTP boundary
- `render.yaml` — optional Render Blueprint for the four services

## Local development

Use one terminal per service:

```bash
# Backend API
pip install -r Backend/requirements.txt
uvicorn Backend.main:app --reload --port 8000

# AI extraction
pip install -r ai_service/requirements.txt
uvicorn ai_service.app.main:app --reload --port 8001

# Frontend
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

The profile page accepts PDF CVs only. The browser checks the extension and
MIME type, while the API also checks the PDF magic header and extracts
selectable text with `pypdf`. Image-only/scanned PDFs are rejected with a
clear error.

Set `ANTHROPIC_API_KEY` in the AI service only when real Anthropic extraction
is wanted. Without it, the response is produced by the clearly documented
offline fallback and is not presented as real AI.

## Privacy behavior

- Raw CV text is used by the candidate-side processing response and remains
  internal to the API's in-memory record.
- Employer proof endpoints return only matching scores, proof status, and
  proof metadata; they do not return extracted CV fields or raw text.
- The Compact circuit writes only an opaque `Bytes<32>` result key and a
  Boolean eligibility result to public ledger state.
- The Python API leaves `MIDNIGHT_SERVICE_URL` empty by default. In that mode,
  proof status is `not_configured`/`local_fallback`, never “verified”.

## Midnight verification

The contract has been compiled and type-checked with the current tested
preprod compatibility set: Compact toolchain `0.31.1`, Compact runtime
`0.16.0`, and Midnight.js `4.1.1`. The Compact devtools installer currently
provides the compiler:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh | sh
export PATH="$HOME/.local/bin:$PATH"
compact update 0.31.1
compact compile contract/verihire.compact midnight_service/managed/verihire
cd midnight_service
npm ci
npm run build
```

For a real preprod proof, also run a compatible proof server, fund a
programmatic wallet, deploy the generated contract, and set the values in
`midnight_service/.env.example`. `WALLET_SEED` is a 32-byte or 64-byte
hexadecimal seed, and `MIDNIGHT_STORAGE_PASSWORD` must be at least 16
characters. Never commit either value.

Current documented preprod endpoints:

- Node: `wss://rpc.preprod.midnight.network`
- Indexer: `https://indexer.preprod.midnight.network/api/v4/graphql`
- Indexer WebSocket:
  `wss://indexer.preprod.midnight.network/api/v4/graphql/ws`
- Proof server: run a compatible `8.1.0` proof server locally or on private
  infrastructure

The repository verification completed the local Compact compilation and
TypeScript build, but no funded wallet, proof server, or live transaction was
available here. Therefore this project does not claim a live proof or
transaction.

## Render

`render.yaml` describes the frontend, backend, AI, and Midnight services.
After creating the services in Render, set the generated public URLs:

- frontend `NEXT_PUBLIC_API_URL` → backend URL
- backend `AI_SERVICE_URL` → AI service URL
- backend `MIDNIGHT_SERVICE_URL` → Midnight service URL, only after the
  contract/wallet/proof infrastructure is ready

Render secrets are marked `sync: false`; enter them in Render rather than
committing `.env` files.

## Checks

```bash
cd frontend && npm run lint && npm run build
cd ../midnight_service && npm run build
cd ../contract && compact compile verihire.compact ../midnight_service/managed/verihire
cd .. && python -m compileall -q Backend ai_service
```