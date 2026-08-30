# VeriHire API Layer — Quick Start

## 5-minute setup

This system is two services: `ai_service/` (CV/job extraction) and
`Backend/` (this directory — the API layer). Start both.

```bash
# terminal 1 — AI extraction service (repo root)
cd ai_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
# no ANTHROPIC_API_KEY needed to try it — it falls back to an offline
# keyword extractor automatically

# terminal 2 — this API layer (repo root)
cd Backend
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000`, ai_service at
`http://localhost:8001`.

## Quick test

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health

# List seed jobs
curl http://localhost:8000/api/jobs

# Register a candidate from raw text
curl -X POST http://localhost:8000/api/candidates \
  -F "cv_text=4 years of Python and PostgreSQL experience, AWS certified, Bachelor's degree." \
  -F "name=Jordan Ellis" -F "email=jordan@example.com"
# → {"candidate_id": "...", "anonymized_ref": "PX-101", ...}

# Register a candidate from a PDF instead
curl -X POST http://localhost:8000/api/candidates \
  -F "file=@/path/to/cv.pdf" -F "name=Jordan Ellis"

# Apply to a job (use the candidate_id from above)
curl -X POST http://localhost:8000/api/candidates/{candidate_id}/apply/job-001

# Employer's view of applicants for that job
curl http://localhost:8000/api/employers/jobs/job-001/candidates

# Candidate discloses contact info for that one application
curl -X POST "http://localhost:8000/api/candidates/{candidate_id}/disclose/job-001?level=full_disclosure"
```

## Features implemented

### Core
- ✓ Two independently-deployable FastAPI services (`ai_service`, `Backend`)
- ✓ Pydantic models on both sides of the AI-extraction contract
- ✓ CORS enabled
- ✓ In-memory storage with 3 seed jobs (2 verified, 1 deliberately unverified)

### Candidate flow
- ✓ Registration from a PDF **or** raw text — same endpoint, `POST /api/candidates`
- ✓ AI extraction (real Claude tool-use call, or offline fallback with no API key)
- ✓ Anonymized reference (`"PX-104"`-style) — never a name/CV in any response before disclosure
- ✓ Apply to a job → graded match (excellent/good/average/poor) + Midnight proof (mock, unless configured)
- ✓ Explicit, per-application progressive disclosure

### Employer flow
- ✓ Post a job (`POST /api/jobs`) → AI parses the description, employer/domain verification runs automatically
- ✓ Check a company/domain without posting a job (`POST /api/jobs/verify-external`)
- ✓ View applicants for a job, contact info gated by disclosure level

## API endpoints summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| POST | `/api/candidates` | Register a candidate (PDF or text) |
| POST | `/api/candidates/{id}/apply/{job_id}` | Apply to a job |
| POST | `/api/candidates/{id}/disclose/{job_id}` | Escalate disclosure |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{job_id}` | Job details |
| POST | `/api/jobs` | Create a job posting |
| POST | `/api/jobs/verify-external` | Check a company/domain |
| GET | `/api/employers/jobs/{id}/candidates` | Applicants for a job |

## Midnight proof

By default `MIDNIGHT_SERVICE_URL` is blank in `.env`, so every proof comes
from `midnight_mock.py` — a same-shaped fake, no real cryptography. To use
a real proof, stand up `../midnight_service/` (see its own README — it
needs the Compact compiler, a local proof server, testnet RPC access, and
a funded wallet, none of which are set up by default) and set
`MIDNIGHT_SERVICE_URL=http://localhost:7000` in `.env`.

## Documentation

- **API docs**: `http://localhost:8000/docs` (Swagger), `/redoc`
- **Full reference**: [README.md](README.md)
- **Architecture & diagrams**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Testing walkthrough**: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Postman collection**: `VeriHire_API_Collection.postman_collection.json`

## Project structure

```
Backend/
├── main.py                 ← Entry point (run this)
├── config.py               ← AI_SERVICE_URL, MIDNIGHT_SERVICE_URL
├── models.py                ← Pydantic schemas
├── database.py              ← In-memory storage
├── rules_engine.py          ← Matching + tier grading
├── ai_client.py             ← Calls ../ai_service
├── employer_verification.py ← Mocked domain registry
├── midnight_client.py       ← Real-service-or-mock switch
├── midnight_mock.py         ← The offline mock
├── api/
│   ├── candidates.py        ← Register/apply/disclose
│   ├── jobs.py               ← Job listing/creation/verification
│   └── employers.py         ← Applicant view for employers
└── data/seed_jobs.json      ← 3 seed jobs
```

## Next steps

1. **Start both services**: `ai_service` on 8001, `Backend` on 8000.
2. **Test manually**: curl commands above, or the Postman collection.
3. **Verify AI extraction**: register a candidate and check the
   `raw_summary`/skills it returns match what you'd expect from the CV text.
4. **Check the rules engine**: apply to different seed jobs and confirm
   tiers make sense.
5. **Try the disclosure flow**: confirm the employer view only shows
   contact info after `disclose(level=full_disclosure)`.

## Troubleshooting

**AI service connection error?**
- Ensure `ai_service` is running on the URL in `AI_SERVICE_URL` (default `http://localhost:8001`).

**Candidate/job/application not found?**
- Storage is in-memory only — a restart of either service clears its state.

**Every proof looks fake / no real blockchain call?**
- Expected by default — see the Midnight proof section above.
