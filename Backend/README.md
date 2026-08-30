# VeriHire API Layer

VeriHire is a recruitment-verification system built around one idea:
**AI extracts a candidate's credentials, deterministic rules decide if
they match a job, and Midnight proves the match without revealing the
underlying data.** A candidate stays anonymous to an employer until they
explicitly choose to disclose contact info.

This directory (`Backend/`) is the API layer that ties the pieces
together. It works alongside a separate `ai_service/` (CV/job-description
extraction) and, optionally, `midnight_service/` (real Midnight ZK
proofs) — see [Related services](#related-services) below.

## Architecture

```
Candidate (PDF or pasted text)          Employer (free-text job description)
        │                                          │
        ▼                                          ▼
  Backend: POST /api/candidates          Backend: POST /api/jobs
        │  (pdfplumber extracts text          │  (calls ai_service /parse-job,
        │   from a PDF, if given)             │   calls employer_verification.py)
        ▼                                          ▼
  ai_client.py → ai_service POST /extract   JobPosting stored, with
        │  (structured ExtractionResult:          verification badges
        │   skills/certs/education)
        ▼
  candidate stored, anonymized_ref returned (e.g. "PX-104")
        │
        ▼
  POST /api/candidates/{id}/apply/{job_id}
        │
        ├─→ rules_engine.evaluate()  →  MatchResult (per-criterion checklist,
        │                                 score 0.0-1.0, tier: excellent/
        │                                 good/average/poor)
        │
        └─→ midnight_client.generate_proof()  →  ProofResult
              │
              ├─ MIDNIGHT_SERVICE_URL set  → real Midnight service (mock today —
              │                               see midnight_service/README.md)
              └─ unset (default)           → midnight_mock.py (offline stand-in)
        │
        ▼
  ApplicationResult returned: anonymized ref, tier, checklist, proof.
  No name, email, or phone — until the candidate calls
  POST /api/candidates/{id}/disclose/{job_id}, which is the only thing
  that ever releases contact info, and only to that one job's employer.
```

## Project structure

```
Backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management (AI_SERVICE_URL, MIDNIGHT_SERVICE_URL)
├── models.py                  # Pydantic data models
├── database.py                # In-memory storage (jobs, candidates, applications) + seed data
├── rules_engine.py            # Deterministic candidate-vs-job matching + tier grading
├── ai_client.py                # HTTP client for the separate ai_service (CV/job extraction)
├── employer_verification.py   # Mocked employer/domain verification registry
├── midnight_client.py         # Picks real Midnight service vs. offline mock
├── midnight_mock.py           # The offline mock (what actually runs today)
├── api/
│   ├── __init__.py
│   ├── candidates.py          # Candidate registration (PDF or text), apply, disclose
│   ├── jobs.py                 # Job listing/creation, employer/domain verification
│   └── employers.py           # Employer's view of who applied to their job
├── data/
│   └── seed_jobs.json          # 3 seed job postings (verified, verified, deliberately unverified)
├── requirements.txt
├── .env                        # Environment configuration
├── .gitignore
├── VeriHire_API_Collection.postman_collection.json
└── README.md
```

## Related services

This API layer doesn't do CV extraction or ZK proofs itself — it delegates
to two sibling services at the repo root:

- **`../ai_service/`** — a FastAPI service with `POST /extract` (CV text →
  structured skills/certifications/education) and `POST /parse-job` (job
  description → structured requirements). Calls Claude via the Anthropic
  API if `ANTHROPIC_API_KEY` is set; otherwise falls back to an offline
  keyword extractor, so it runs without a key. See `../ai_service/README`
  in its own directory (or its `app/` docstrings) for details.
- **`../midnight_service/`** and **`../contract/verihire.compact`** — a
  real Compact smart contract and a Node/TypeScript service that would
  call it. **Not yet compiled or deployed** — see
  `../midnight_service/README.md` for the toolchain needed (Compact
  compiler, local proof server, testnet RPC, funded wallet). Until
  `MIDNIGHT_SERVICE_URL` is set and pointed at a real running instance,
  every proof in this app comes from `midnight_mock.py`.

## Dependencies

- **FastAPI** — web framework
- **Uvicorn** — ASGI server
- **Pydantic / pydantic-settings** — data validation and settings
- **httpx** — async/sync HTTP client for calling `ai_service` and (optionally) `midnight_service`
- **pdfplumber** — PDF text extraction
- **python-multipart** — multipart form/file upload support

## Setup

### 1. Install dependencies

```bash
cd Backend
pip install -r requirements.txt
```

### 2. Configure environment

Edit `.env` if needed:
```
AI_SERVICE_URL=http://localhost:8001

# Leave blank to use the offline mock proof. Set once midnight_service/ is
# actually running to switch on real Midnight proofs.
MIDNIGHT_SERVICE_URL=
```

### 3. Run both services

```bash
# terminal 1 — AI extraction service
cd ai_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# terminal 2 — this API layer
cd Backend
pip install -r requirements.txt
python main.py
```

The API is available at `http://localhost:8000`, docs at
`http://localhost:8000/docs` (Swagger) and `/redoc`. `ai_service` docs are
at `http://localhost:8001/docs`.

## Features

### 1. Candidate registration (`POST /api/candidates`)

Accepts **either** a PDF file upload **or** raw CV text — exactly one of
the two:

**As a PDF (multipart/form-data):**
```
- file: PDF file upload
- name, email, phone: optional form fields
```

**As raw text (multipart/form-data, no file):**
```
- cv_text: string
- name, email, phone: optional form fields
```

A PDF is run through `pdfplumber` to extract its text first; both paths
then call `ai_client.extract_cv()` (real Claude call or offline fallback,
depending on `ai_service`'s configuration) to turn the text into a
structured `ExtractionResult`. The response never includes the raw CV
text, name, email, phone, or extracted credentials — only a
`candidate_id` and an `anonymized_ref` (e.g. `"PX-104"`), which is all a
caller needs to continue the flow.

### 2. Applying to a job (`POST /api/candidates/{id}/apply/{job_id}`)

Runs the rules engine (see below) and then Midnight proof generation
(real or mocked), and returns an `ApplicationResult`: the candidate's
anonymized ref, the `MatchResult` (per-criterion checklist + score + tier),
the `ProofResult`, and `contact: null` — no personal information at this
stage.

### 3. Rules engine

Evaluates a candidate's `ExtractionResult` against a job's
`JobRequirements`:

- **Skills**: each required skill maps to a minimum years figure (`0`
  means "must simply be present"). The candidate's `skills` dict is
  checked per-skill.
- **Certifications**: each required certification must appear in the
  candidate's certification list.
- **Education**: compared against an ordered scale (`none` <
  `highschool` < `bachelors` < `masters` < `phd`); `equivalent_experience`
  always satisfies any requirement.

**Grading** (`score` = fraction of criteria satisfied, `tier` derived from it):
- All criteria met → **excellent**
- `score >= 0.75` → **good**
- `score >= 0.5` → **average**
- otherwise → **poor**

`overall_match` is `true` only when every criterion is satisfied.

### 4. Midnight proof (`midnight_client.py`)

- `MIDNIGHT_SERVICE_URL` unset (default) → `midnight_mock.py` generates a
  same-shaped fake proof (`verified` mirrors the rules engine's own
  verdict) — no network call, no real cryptography.
- `MIDNIGHT_SERVICE_URL` set → POSTs the candidate's private extraction
  data plus the job's public requirements to that service's `/prove`
  endpoint. On any failure, falls back to the mock rather than breaking
  the request.
- The private inputs sent are deliberately the **raw** values (skills,
  certs, education), not the already-computed match booleans — a real
  Midnight circuit needs to do its own private computation for the proof
  to mean anything. See `midnight_client.py`'s docstring and
  `../contract/verihire.compact` for exactly which four criteria the
  current circuit shape covers (Python years, PostgreSQL presence, AWS
  certification, Bachelor's-or-equivalent) — a known MVP limitation for
  jobs that need other criteria.

### 5. Progressive disclosure (`POST /api/candidates/{id}/disclose/{job_id}`)

The candidate explicitly moves their disclosure level forward
(`anonymous` → `verified_candidate` → `full_disclosure`) for one specific
application. Only reaching `full_disclosure` populates `contact` with
name/email/phone — and only for that one job. Nothing else in the system
escalates disclosure automatically.

### 6. Employer verification (`POST /api/jobs`, `POST /api/jobs/verify-external`)

`employer_verification.py` checks a company/domain against a small
hardcoded "known good" registry. Posting a job (`POST /api/jobs`) runs
both this check and `ai_service`'s `/parse-job` extraction, and stores the
result alongside the job. `POST /api/jobs/verify-external` runs the same
check for a company/domain that isn't even posted on VeriHire — useful for
a candidate to sanity-check a suspicious-looking listing before engaging
with it at all.

### 7. Employer's view of applicants (`GET /api/employers/jobs/{job_id}/candidates`)

Returns every `ApplicationResult` for a job. `contact` is stripped for any
candidate below `full_disclosure`, even though `disclose()` only ever
populates it at that level — belt and suspenders.

## Seed data

Three seed jobs ship in `data/seed_jobs.json`, chosen to demonstrate both
the matching and the verification stories:

1. **job-001** — Backend Engineer, Example Technologies (verified employer).
   Requires 3+ years Python, PostgreSQL, AWS, an AWS certification, and a
   Bachelor's or equivalent.
2. **job-002** — Senior Backend Engineer, Northwind Systems (verified
   employer). Requires 5+ years Python, 2+ years PostgreSQL, Docker,
   Kubernetes.
3. **job-003** — "Senior Backend Developer — URGENT, $5,000/month",
   UnknownCompany123 (**deliberately unverified** — every verification
   flag is `false`). This is the "suspicious job" demo scenario: a
   candidate checking this listing via `GET /api/jobs` or
   `POST /api/jobs/verify-external` immediately sees it's unverified,
   before ever sending a CV.

A sample CV and job description for manual testing live in
`../ai_service/samples/`.

## API endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check (also reports jobs loaded) |
| POST | `/api/candidates` | Register a candidate from a PDF or raw CV text |
| POST | `/api/candidates/{id}/apply/{job_id}` | Apply to a job — match + proof |
| POST | `/api/candidates/{id}/disclose/{job_id}` | Escalate disclosure for one application |
| GET | `/api/jobs` | List all active jobs |
| GET | `/api/jobs/{job_id}` | Get one job's details |
| POST | `/api/jobs` | Create a job posting (runs AI #2 + employer verification) |
| POST | `/api/jobs/verify-external` | Check a company/domain not posted on VeriHire |
| GET | `/api/employers/jobs/{job_id}/candidates` | Employer's view of applicants for their job |

## Testing

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for step-by-step scenarios, and
`VeriHire_API_Collection.postman_collection.json` for a Postman collection.

## Common issues

### AI service connection error
- Check that `ai_service` is running on the URL configured in `AI_SERVICE_URL` (default `http://localhost:8001`).
- Without `ANTHROPIC_API_KEY` set on `ai_service`, it silently falls back to offline keyword extraction — this is expected, not an error, but extraction quality will be much rougher.

### Pydantic validation error
- `ai_service` and this backend independently define `ExtractionResult`/`JobRequirements` (see `models.py`'s module docstring for why) — if you change one, change the other, and check the repo-root `SCHEMA_CONTRACT.md`... *(not yet ported into this repo — see Future Enhancements below)*.

### Candidate/job/application not found
- All storage is in-memory (`database.py`) — restarting `python main.py` clears everything. `candidate_id`, `job_id`, and disclosure state all reset.

### Every proof comes back `verified: true/false` but never talks to a real blockchain
- Expected until `midnight_service/` is actually compiled, deployed, and `MIDNIGHT_SERVICE_URL` is set — see [Related services](#related-services).

## Future enhancements

- [ ] Persistent database (PostgreSQL/MongoDB) in place of `database.py`'s in-memory dicts
- [ ] Actually stand up `midnight_service/` (Compact compiler, proof server, funded testnet wallet) and set `MIDNIGHT_SERVICE_URL`
- [ ] Port `SCHEMA_CONTRACT.md` into this repo so the AI-shared model contract has one home
- [ ] Generalize the Midnight circuit beyond the current fixed four criteria
- [ ] Real employer/domain verification (DNS ownership, verified email) in place of the hardcoded registry
- [ ] Authentication on the employer-facing endpoints

## License

Part of the VeriHire project.
