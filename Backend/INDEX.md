# VeriHire API Layer — Documentation Index

This directory (`Backend/`) is one of three services in the VeriHire repo
root: `Backend/` (this one), `ai_service/`, and `contract/` +
`midnight_service/`. This file indexes the docs that live here.

## Start here

| If you want to... | Read this |
|---|---|
| Get running in 5 minutes | [QUICKSTART.md](QUICKSTART.md) |
| Understand how it works | [README.md](README.md) |
| See the architecture and data flow | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Run through test scenarios | [TESTING_GUIDE.md](TESTING_GUIDE.md) |
| See what's implemented vs. still mocked | [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) |
| Check delivered-vs-outstanding items | [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) |
| Understand PDF upload specifically | [PDF_UPLOAD_FEATURE.md](PDF_UPLOAD_FEATURE.md) / [PDF_QUICK_SUMMARY.md](PDF_QUICK_SUMMARY.md) |

## Documentation map

1. **QUICKSTART.md** — 5-minute setup for both `ai_service` and `Backend`, quick curl tests, endpoint summary.
2. **README.md** — full reference: architecture, project structure, dependencies, setup, every feature and endpoint, seed data, troubleshooting.
3. **TESTING_GUIDE.md** — step-by-step scenarios covering job listing/verification, candidate registration (text and PDF), applying, disclosure, and error cases.
4. **ARCHITECTURE.md** — diagrams: system architecture, candidate-applies-to-job data flow, rules engine algorithm, tier interpretation, error handling, in-memory storage schema, deployment sketch.
5. **IMPLEMENTATION_SUMMARY.md** — what's built, what's still mocked (notably Midnight), data models, design patterns.
6. **COMPLETION_REPORT.md** — current status snapshot: what's real vs. mocked, metrics, next steps.
7. **DELIVERY_CHECKLIST.md** — checklist of what's actually in the repo today.
8. **PDF_QUICK_SUMMARY.md** / **PDF_UPLOAD_FEATURE.md** — PDF-specific detail: `POST /api/candidates` accepts a PDF upload as an alternative to raw `cv_text`.

## File organization

```
Backend/
├── main.py, config.py, models.py, database.py
├── rules_engine.py, ai_client.py, employer_verification.py
├── midnight_client.py, midnight_mock.py
├── api/
│   ├── candidates.py    # register / apply / disclose
│   ├── jobs.py           # list / get / create / verify-external
│   └── employers.py     # view applicants for a job
├── data/seed_jobs.json
├── requirements.txt, .env, .gitignore
├── VeriHire_API_Collection.postman_collection.json
└── (this documentation set)
```

Sibling directories at the repo root (not inside `Backend/`):
```
ai_service/        # CV/job-description extraction (real Claude call + offline fallback)
contract/          # verihire.compact — the Midnight ZK contract (not yet compiled)
midnight_service/  # Node/TS service that would call it (not yet deployed)
```

## Quick navigation by task

**"I want to run the API"** → [QUICKSTART.md](QUICKSTART.md), then `python main.py` (after starting `ai_service` too).

**"I need to test the API"** → [TESTING_GUIDE.md](TESTING_GUIDE.md), or the Postman collection.

**"I need to integrate a frontend"** → [README.md](README.md#api-endpoints) for the endpoint list, [ARCHITECTURE.md](ARCHITECTURE.md) for data flow and response shapes.

**"I need to modify the rules engine"** → read [rules_engine.py](rules_engine.py), cross-reference [ARCHITECTURE.md](ARCHITECTURE.md#rules-engine-algorithm).

**"I need to add a new job"** → edit [data/seed_jobs.json](data/seed_jobs.json), matching the `JobPosting`/`JobRequirements` shape in [models.py](models.py).

**"I need to actually run the Midnight proof for real"** → see `../midnight_service/README.md`, then set `MIDNIGHT_SERVICE_URL` in `.env`.

## Troubleshooting

| Issue | Where to look |
|---|---|
| Can't start either service | [QUICKSTART.md](QUICKSTART.md#troubleshooting) |
| AI extraction looks wrong/rough | [README.md](README.md#common-issues) — likely running in offline fallback mode |
| Candidate/job/application 404 | Storage is in-memory — check nothing restarted |
| Every proof is fake | Expected by default — see [README.md](README.md#related-services) |

## Status

- **Date**: August 30, 2026
- **Status**: Candidate/job/employer flow and AI extraction are real and working end-to-end (verified via an in-process smoke test). Midnight proof generation is mock-only — see [COMPLETION_REPORT.md](COMPLETION_REPORT.md) for the honest real-vs-mocked breakdown.
