# VeriHire API Layer — Status Report

**Location**: `Backend/` (repo root also has sibling `ai_service/`,
`contract/`, `midnight_service/`)
**Date**: August 30, 2026

## Summary

This is a merge of two independently-built implementations of the same
system into one working API layer: candidate registration (PDF or text)
→ AI extraction → deterministic rules-engine matching → Midnight proof
(mock today, real service scaffolded but not deployed) → progressive
disclosure. Verified end-to-end with both services running live and an
in-process smoke test covering every endpoint.

## What's real vs. mocked

| Piece | Status |
|---|---|
| Candidate registration (PDF and raw text) | **Real**, tested |
| CV → structured credentials (AI extraction) | **Real** Claude call (or offline keyword fallback without an API key) — tested both paths |
| Job description → structured requirements (AI extraction) | **Real** Claude call (or offline fallback) — tested |
| Candidate-vs-job rule matching + scoring/tiers | **Real**, deterministic Python — tested |
| Employer/domain verification | **Mocked** — a small hardcoded registry in `employer_verification.py` |
| Progressive disclosure | **Real** — tested (contact info correctly gated and released) |
| **Midnight ZK proof** | **NOT running for real.** `contract/verihire.compact` and `midnight_service/` are real code (Compact contract + Node/TS service) but have not been compiled, deployed, or run in this environment — no Compact compiler, proof server, node/indexer access, or funded wallet available here. Every proof today comes from `midnight_mock.py`. See `midnight_service/README.md` for exactly what's needed to make it real. |
| Data storage | In-memory (`database.py`) — resets on restart |

## Verification performed

- Every Python file in `Backend/` and `ai_service/` compiles cleanly (no syntax errors) and imports end-to-end.
- Both services started live (`ai_service` on 8001, `Backend` on 8000) and exercised with a full smoke test:
  - Job listing, including the deliberately-unverified "phishing" seed job
  - `verify-external` for both a known-good and unknown domain
  - Candidate registration via raw text and via an actual generated PDF
  - Applying to a strong-match job → `tier: excellent`, mock proof `verified: true`
  - Employer view correctly hides contact info before disclosure
  - Disclosure correctly reveals contact info, scoped to that one job only

## File structure

```
Backend/
├── APPLICATION CODE
│  ├── main.py, config.py, models.py, database.py
│  ├── rules_engine.py, ai_client.py, employer_verification.py
│  ├── midnight_client.py, midnight_mock.py
│  └── api/{candidates,jobs,employers}.py
├── DATA
│  └── data/seed_jobs.json
├── CONFIGURATION
│  └── requirements.txt, .env, .gitignore
├── DOCUMENTATION
│  └── README, QUICKSTART, TESTING_GUIDE, ARCHITECTURE,
│      IMPLEMENTATION_SUMMARY, DELIVERY_CHECKLIST, INDEX,
│      PDF_QUICK_SUMMARY, PDF_UPLOAD_FEATURE (this set)
└── TESTING
   └── VeriHire_API_Collection.postman_collection.json

../ai_service/         (sibling service)
../contract/, ../midnight_service/   (Midnight — not yet deployed)
```

## API endpoints (8 total + health)

```
GET  /health
POST /api/candidates
POST /api/candidates/{id}/apply/{job_id}
POST /api/candidates/{id}/disclose/{job_id}
GET  /api/jobs
GET  /api/jobs/{job_id}
POST /api/jobs
POST /api/jobs/verify-external
GET  /api/employers/jobs/{job_id}/candidates
```

## Integration points

```python
# ai_service — Backend/.env
AI_SERVICE_URL=http://localhost:8001
# Endpoints used: POST /extract, POST /parse-job

# midnight_service — Backend/.env (optional)
MIDNIGHT_SERVICE_URL=
# Blank = midnight_mock.py used. Set once ../midnight_service/ is
# actually running (see its README) to switch on real proofs.
```

## Honest next steps

### To make Midnight real (the one piece still mocked)
Follow `../midnight_service/README.md`: install the Compact compiler,
compile `../contract/verihire.compact`, run a local proof server, get
testnet RPC endpoints, fund a wallet, deploy, set
`MIDNIGHT_SERVICE_URL`. This is real engineering time, not a config
change.

### Everything else
- Swap `database.py`'s in-memory dicts for a real database if persistence across restarts matters
- Generalize the Midnight circuit shape beyond the current fixed four criteria
- Real employer/domain verification instead of the hardcoded registry
- Add authentication, particularly to the employer-facing endpoints
- Wire a frontend against the endpoints above (not part of this pass)

## Conclusion

The candidate/job/employer flow, AI extraction, rules engine, and
progressive disclosure are real and verified end-to-end. Midnight proof
generation is functionally complete via the mock and structurally ready
for the real service — it is not yet cryptographically real. Treat this
as an accurate status, not a "fully done" claim.
