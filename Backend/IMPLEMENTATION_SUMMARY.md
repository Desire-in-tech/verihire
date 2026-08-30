# VeriHire API Layer — Implementation Summary

## Project overview

`Backend/` is the API layer for VeriHire: candidate registration and
progressive disclosure, job posting with employer/domain verification,
deterministic candidate-vs-job matching, and a Midnight proof step (real
service or offline mock, switchable via config). It calls out to a
sibling `ai_service/` for all AI extraction — no LLM call happens inside
this service directly.

## What's implemented

### 1. FastAPI project structure ✓
- `main.py`, `config.py`, `requirements.txt`, `.env`
- CORS enabled (no credentials, since none are used)
- Swagger/ReDoc at `/docs` and `/redoc`

### 2. Seed dataset ✓
- `data/seed_jobs.json`: 3 jobs —
  - job-001: Backend Engineer, Example Technologies (verified)
  - job-002: Senior Backend Engineer, Northwind Systems (verified)
  - job-003: "URGENT" listing, UnknownCompany123 (deliberately unverified — every verification flag `false`)

### 3. Candidate registration ✓
```
POST /api/candidates
Input: multipart form — either `file` (PDF) or `cv_text`, plus optional name/email/phone
Output: { candidate_id, anonymized_ref, cv_source, disclosure_level }
```
- PDF path extracts text via `pdfplumber` before calling AI extraction; text path calls it directly — same downstream flow either way.
- Response never includes PII, raw CV text, or the structured extraction (`response_model_exclude`).

### 4. Rules engine ✓
**File**: `rules_engine.py`

- Per-skill years comparison (`dict[str, int]` on both the requirement and candidate side)
- Certification presence check
- Education level comparison against an ordered scale, with `equivalent_experience` always satisfying
- Score = fraction of criteria satisfied; tier = excellent (all met) / good (≥0.75) / average (≥0.5) / poor
- `overall_match` is `true` only at "excellent"

### 5. AI service integration ✓
**File**: `ai_client.py`, calling the sibling `ai_service/`

- `extract_cv(text)` → `ExtractionResult`
- `extract_job_requirements(description)` → `JobRequirements`
- Raises a clear `HTTPException` (502) on connection failure or schema mismatch, rather than letting a low-level error bubble up
- `ai_service` itself calls Claude via tool-use when `ANTHROPIC_API_KEY` is set, falling back to an offline keyword extractor otherwise — tested, both paths work

### 6. Employer verification ✓
**File**: `employer_verification.py`

- Small hardcoded domain registry (`example-technologies.com`, `northwind-systems.com`)
- Unknown domains come back fully unverified — this is what powers the job-003 "suspicious job" seed scenario

### 7. Midnight proof ✓ (mock) / real service not yet deployed
**Files**: `midnight_client.py`, `midnight_mock.py`, `../contract/verihire.compact`, `../midnight_service/`

- `midnight_client.generate_proof()` is the single decision point: real service if `MIDNIGHT_SERVICE_URL` is set and reachable, offline mock otherwise (including on any failure calling the real service)
- The mock produces a same-shaped `ProofResult` with `verified` mirroring the rules engine's own verdict — no real cryptography
- The real contract (`verihire.compact`) and Node/TS service (`midnight_service/`) are present in the repo but **not compiled or deployed** — see `midnight_service/README.md` for the toolchain needed
- The circuit's shape is fixed to four criteria (Python years, PostgreSQL, AWS cert, Bachelor's-or-equivalent) — a known limitation for jobs needing other criteria (see `midnight_client.py`'s `_map_to_circuit_inputs` docstring)

### 8. Progressive disclosure ✓
- `DisclosureLevel`: `anonymous` → `verified_candidate` → `full_disclosure`
- `POST /api/candidates/{id}/disclose/{job_id}` is the only thing that ever populates `contact` on an `ApplicationResult`, and only for that one job
- Employer-facing endpoint (`GET /api/employers/jobs/{id}/candidates`) independently strips `contact` for anyone below `full_disclosure`

### 9. Testing ✓
- Postman collection (`VeriHire_API_Collection.postman_collection.json`)
- [TESTING_GUIDE.md](TESTING_GUIDE.md) with scenarios covering jobs, verification, registration (both PDF and text), applying, disclosure, and error cases
- An in-process smoke test exercising the full flow end-to-end (register via text, register via PDF, apply to a strong-match and a weak-match job, disclose, verify employer-side gating) was run against live `ai_service` + `Backend` instances during development and passed

---

## Project structure

```
Backend/
├── main.py                    # FastAPI entry point
├── config.py                  # AI_SERVICE_URL, MIDNIGHT_SERVICE_URL
├── models.py                  # Pydantic schemas
├── database.py                # In-memory storage + seed loading
├── rules_engine.py            # Matching + tier grading
├── ai_client.py                # ai_service HTTP client
├── employer_verification.py   # Mocked domain registry
├── midnight_client.py         # Real-service-or-mock switch
├── midnight_mock.py           # The offline mock
├── api/
│   ├── candidates.py
│   ├── jobs.py
│   └── employers.py
├── data/seed_jobs.json
├── requirements.txt, .env
└── (documentation)

../ai_service/                 # sibling service, not inside Backend/
../contract/verihire.compact   # Midnight contract, not yet compiled
../midnight_service/           # Node/TS service, not yet deployed
```

## Data models

All Pydantic v2, defined in `models.py`:

1. **EducationLevel** — enum
2. **ExtractionResult** — `skills: dict[str,int]`, certifications, education, raw_summary (shared contract with `ai_service`)
3. **JobRequirements** — required skills/certs/min education (shared contract with `ai_service`)
4. **DisclosureLevel** — enum
5. **CVSubmission** — legacy text-only input shape (superseded in practice by `api/candidates.py`'s multipart handling, kept for reference)
6. **CandidateProfile** — private candidate record
7. **EmployerVerificationResult**
8. **JobCreateRequest**, **JobPosting**
9. **CriterionResult**, **MatchTier**, **MatchResult** — rules engine output
10. **ProofResult** — Midnight (real or mock) output
11. **ApplicationResult** — what an employer sees

## Integration points

### ai_service
- URL: `AI_SERVICE_URL` in `.env` (default `http://localhost:8001`)
- Endpoints used: `POST /extract`, `POST /parse-job`

### midnight_service (optional, real proofs)
- URL: `MIDNIGHT_SERVICE_URL` in `.env` (blank by default → mock)
- Endpoint used: `POST /prove`
- Status: not yet compiled/deployed — see `../midnight_service/README.md`

### Frontend
- Not part of this pass. Endpoints are documented in [README.md](README.md#api-endpoints) and ready to integrate against.

## Design patterns used

- Dependency-light service boundary: `ai_client.py`/`midnight_client.py` are the *only* files that make outbound HTTP calls; everything else is pure Python or in-memory storage
- Deterministic rules, not an AI judgment call, decide eligibility — the AI's only job is extraction
- Real-vs-mock fallback pattern used twice (AI offline extractor, Midnight mock) so the system runs end-to-end without external dependencies configured
- Progressive disclosure as an explicit, candidate-initiated action, never automatic

## Known limitations / future work

- In-memory storage only (`database.py`) — resets on restart
- Midnight proof generation is mock-only until `midnight_service/` is actually deployed
- The Midnight circuit's fixed four-criteria shape doesn't generalize to arbitrary job requirements
- Employer/domain verification is a hardcoded registry, not real DNS/identity verification
- No authentication on any endpoint
