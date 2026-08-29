# VeriHire — Backend + AI + Midnight MVP

This implements the vertical slice described in the pitch doc, end to end:

**Candidate submits a CV on a Candidate UI → CV is parsed into JSON → an
employer lists criteria on an Employer UI → those criteria are parsed into
JSON → the rules engine matches the two → the match is passed toward
Midnight to prove it → the employer sees a graded result (excellent /
good / average / poor), not the raw CV.**

Read **"What's real vs. mocked" below before you demo this** — it matters,
especially the Midnight section.

## The pieces

- **`frontend/candidate.html`** and **`frontend/employer.html`** — the two
  UIs. Plain HTML/CSS/JS, no build step, no framework — just `fetch()`
  calls to the backend. Open either one directly from disk, or serve them
  with `python3 -m http.server 8080` from inside `frontend/`.
- **`ai_service/`** — the AI integration part (your part). One endpoint
  turns CV text into structured JSON (`/extract`), another turns an
  employer's free-text criteria into structured JSON (`/parse-job`). Calls
  Claude via the Anthropic API; falls back to an offline keyword extractor
  if no API key is set, so it still runs without one.
- **`backend/`** — the backend/API part (your teammate's part). Job
  listings, candidate records, the deterministic rules engine that grades
  a candidate against a job's requirements, the mocked
  employer-verification check, and the Midnight proof step.
- **`contract/verihire.compact`** and **`midnight_service/`** — the actual
  Midnight integration: a real Compact smart contract plus a Node/TypeScript
  service that would call it. See the honesty section below — this part is
  real code, not yet a running system.

They only ever talk to each other over HTTP + JSON — see
**`SCHEMA_CONTRACT.md`** for the exact field names and types every piece
agrees on.

```
 Candidate UI                                    Employer UI
      │  CV text                                       │  free-text criteria
      ▼                                                 ▼
 ai_service /extract                          ai_service /parse-job
      │  (structured JSON)                              │  (structured JSON)
      ▼                                                 ▼
 ExtractionResult (private)  ───►  backend rules_engine.py  ◄─── JobRequirements (public)
                                          │
                                          ▼
                          MatchResult: per-criterion checklist,
                          score, tier (excellent/good/average/poor)
                                          │
                                          ▼
                              backend midnight_client.py
                          ┌───────────────┴───────────────┐
                          ▼                                ▼
              MIDNIGHT_SERVICE_URL set              MIDNIGHT_SERVICE_URL unset
              → real Midnight service                → offline mock proof
              (contract/verihire.compact,             (midnight_mock.py -
               midnight_service/ - NOT YET RUN)         what actually runs today)
                          │                                │
                          └───────────────┬───────────────┘
                                          ▼
                       ApplicationResult - what the employer UI shows:
                       anonymized ref, tier, checklist, proof status.
                       No CV, no contact info, until the candidate
                       explicitly discloses it for that one job.
```

## Running it

Each Python service has its own virtualenv and its own `.env` (copy the
`.env.example` in each folder). This part is fully working — tested
end-to-end in this environment.

```bash
# terminal 1 — AI extraction service
cd ai_service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY, or leave it blank for offline fallback mode
uvicorn app.main:app --reload --port 8001

# terminal 2 — backend API
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # leave MIDNIGHT_SERVICE_URL blank until midnight_service/ is actually running
uvicorn app.main:app --reload --port 8000

# terminal 3 — the two UIs
cd frontend
python3 -m http.server 8080
# open http://localhost:8080/candidate.html and http://localhost:8080/employer.html
```

FastAPI also gives you interactive docs for free at
`http://localhost:8001/docs` and `http://localhost:8000/docs`, and there's
a Postman collection at `postman/VeriHire.postman_collection.json` too.

### Run the full demo end-to-end (no UI needed)

```bash
pip install httpx   # if not already installed in whichever env you run this from
python3 scripts/demo.py
```

Walks through all four pitch-doc scenes against the live services from the
command line — useful for a quick sanity check or as a rehearsal script
alongside the actual UI.

## What's real vs. mocked — read this before you demo

| Piece | Status |
|---|---|
| Candidate UI / Employer UI | **Real, working** — plain HTML/JS calling the live backend. |
| CV → structured credentials (AI #1) | **Real** Claude call (or offline fallback without a key) — tested. |
| Job description → structured requirements (AI #2) | **Real** Claude call (or offline fallback) — tested. |
| Candidate-vs-job rule matching + scoring/tiers | **Real**, deterministic Python — tested. Not an AI call, on purpose (see rules_engine.py). |
| Employer/domain verification | **Mocked** — a small hardcoded registry in `employer_verification.py`. |
| **Midnight ZK proof** | **NOT running.** `contract/verihire.compact` is a real Compact contract and `midnight_service/` is a real Node/TypeScript service, both written against Midnight's current public docs and checked npm package versions — but neither has been compiled, deployed, or run in this environment (no Compact compiler, no Midnight node/indexer, no proof server, no funded wallet were available here). Until your team stands that up and sets `MIDNIGHT_SERVICE_URL`, every "proof" in this app comes from `backend/app/midnight_mock.py`, a same-shaped fake. **This is the one part of the AI track's requirement ("Midnight protects the data or verifies the behavior") that is not yet satisfied for real** — see `midnight_service/README.md` for exactly what's needed to make it real, and budget real time for it. |
| Data storage | In-memory (`store.py`) — resets when the process restarts. |

Swapping the mock for the real thing should only require standing up
`midnight_service/` and setting one env var — nothing else in the codebase
needs to change, by design.

## Folder structure

```
verihire-mvp/
├── SCHEMA_CONTRACT.md           shared JSON schema every piece relies on — read this first
├── README.md                    this file
├── frontend/
│   ├── candidate.html           candidate UI: submit CV, browse/apply to jobs, disclose contact info
│   └── employer.html            employer UI: post a job, check an employer/domain, view applicants
├── ai_service/                  AI integration (your part)
│   ├── app/
│   │   ├── main.py               FastAPI app, the two HTTP endpoints
│   │   ├── config.py             env var / API key handling
│   │   ├── models.py             request/response shapes (Pydantic)
│   │   ├── prompts.py            the actual prompts sent to Claude
│   │   └── extraction.py         calls Claude (or offline fallback) to do the extraction
│   ├── samples/                  sample CV + job description for manual testing
│   ├── requirements.txt
│   └── .env.example
├── backend/                      backend/API (teammate's part)
│   ├── app/
│   │   ├── main.py                FastAPI app, CORS, wires up the routes below
│   │   ├── config.py              env var handling (ai_service / midnight_service URLs)
│   │   ├── models.py              every data shape the backend uses (incl. score/tier)
│   │   ├── store.py               in-memory "database"
│   │   ├── ai_client.py           HTTP client that calls ai_service
│   │   ├── rules_engine.py        deterministic candidate-vs-job matching + tiering
│   │   ├── midnight_client.py     picks real Midnight service vs. offline mock
│   │   ├── midnight_mock.py       the offline mock (what actually runs today)
│   │   ├── employer_verification.py   mocked employer/domain verification
│   │   └── routes/
│   │       ├── jobs.py             job listing/creation/verification endpoints
│   │       ├── candidates.py       candidate registration/apply/disclose endpoints
│   │       └── employers.py        employer's view of who applied
│   ├── data/jobs_seed.json        a few seed job postings, loaded on startup
│   ├── requirements.txt
│   └── .env.example
├── contract/
│   └── verihire.compact           the real Midnight smart contract (not yet compiled/deployed)
├── midnight_service/              Node/TypeScript service that would call it (not yet run)
│   ├── src/{server,deploy,providers}.ts
│   ├── package.json
│   └── README.md                  exact toolchain setup steps (compiler, proof server, wallet)
├── scripts/demo.py                end-to-end script that runs the whole pitch-doc demo
└── postman/VeriHire.postman_collection.json
```

## Suggested next steps, roughly in priority order

1. **Get Midnight actually running.** This is the one piece standing
   between "looks like the pitch" and "is the pitch." Follow
   `midnight_service/README.md` — compile the contract, run a local proof
   server, get testnet RPC endpoints, fund a wallet, deploy, set
   `MIDNIGHT_SERVICE_URL`. Budget real hours for this, not minutes.
2. Agree on `SCHEMA_CONTRACT.md` together before changing either service's
   `models.py` — that's the one thing most likely to break silently.
3. Decide whether the fixed four-criteria circuit shape is good enough for
   the demo, or whether you need it to cover more of the seed jobs (see
   `midnight_client.py`'s `_map_to_circuit_inputs` docstring).
4. Replace `store.py`'s in-memory dicts with SQLite if persistence across
   restarts turns out to matter for the demo.
