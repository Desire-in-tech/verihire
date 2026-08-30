# VeriHire Architecture Overview

## System architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (not in this repo pass)               │
│         Candidate: submit CV, browse jobs, apply, disclose           │
│         Employer: post a job, verify a company, view applicants      │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ HTTP
                                ▼
     ┌───────────────────────────────────────────────────┐
     │              Backend/  — API layer (FastAPI)        │
     │                                                     │
     │  ┌───────────────────────────────────────────┐    │
     │  │ POST /api/candidates                       │    │
     │  │ POST /api/candidates/{id}/apply/{job_id}    │    │
     │  │ POST /api/candidates/{id}/disclose/{job_id} │    │
     │  │ GET  /api/jobs                              │    │
     │  │ GET  /api/jobs/{job_id}                     │    │
     │  │ POST /api/jobs                              │    │
     │  │ POST /api/jobs/verify-external              │    │
     │  │ GET  /api/employers/jobs/{id}/candidates    │    │
     │  └───────────────────────────────────────────┘    │
     │                        ▼                            │
     │  ┌───────────────────────────────────────────┐    │
     │  │ database.py — in-memory jobs/candidates/    │    │
     │  │ applications tables                         │    │
     │  └───────────────────────────────────────────┘    │
     │                        ▼                            │
     │  ┌────────────────┐  ┌────────────────┐  ┌────────┐│
     │  │ ai_client.py   │  │ rules_engine.py│  │employer││
     │  │ (calls out)    │  │ (pure Python)  │  │_verif  ││
     │  └───────┬────────┘  └────────────────┘  └────────┘│
     │          │                                          │
     │          │           ┌────────────────────────────┐│
     │          │           │ midnight_client.py           ││
     │          │           │  → midnight_mock.py, or       ││
     │          │           │  → real Midnight service      ││
     │          │           └───────────┬────────────────┘│
     └──────────┼───────────────────────┼─────────────────┘
                │ HTTP                  │ HTTP (if MIDNIGHT_SERVICE_URL set)
                ▼                       ▼
     ┌────────────────────┐   ┌──────────────────────────┐
     │  ai_service/         │   │  midnight_service/          │
     │  POST /extract       │   │  POST /prove                │
     │  POST /parse-job     │   │  (Node/TS, wraps the real    │
     │  (Claude tool-use,   │   │   @midnight-ntwrk SDK against│
     │   offline fallback)  │   │   contract/verihire.compact) │
     └────────────────────┘   │  NOT YET compiled/deployed   │
                                └──────────────────────────┘
```

---

## Data flow: candidate applies to a job

```
1. CANDIDATE REGISTRATION
   Client
     │
     └─→ POST /api/candidates  (PDF file, or {cv_text, name?, email?, phone?})
           │
           ├─ if PDF: pdfplumber extracts text (api/candidates.py)
           │
           └─→ ai_client.extract_cv(text)
                 │
                 └─→ HTTP POST ai_service /extract
                       │
                       ▼
                    Claude tool-use call, or offline keyword fallback
                       │
                       └─→ ExtractionResult
                             { skills: {"python": 4, ...},
                               certifications: [...],
                               education_level: "bachelors",
                               raw_summary: "..." }
           │
           └─→ CandidateProfile stored (private) — response returns only
                 candidate_id + anonymized_ref (e.g. "PX-104")


2. APPLYING TO A JOB
   Client
     │
     └─→ POST /api/candidates/{id}/apply/{job_id}
           │
           ├─→ rules_engine.evaluate(ref, job_id, extraction, job.requirements)
           │     │
           │     ├─ per required skill: candidate_years >= min_years?
           │     ├─ per required cert: present in candidate certs?
           │     ├─ education: candidate level >= required level (or
           │     │  "equivalent_experience", which always satisfies)?
           │     │
           │     └─→ MatchResult { criteria: [...], score, tier, overall_match }
           │
           └─→ midnight_client.generate_proof(match, extraction, requirements)
                 │
                 ├─ MIDNIGHT_SERVICE_URL unset → midnight_mock.generate_proof(match)
                 │     (proof_id, verified = match.overall_match, claim, claim_hash)
                 │
                 └─ MIDNIGHT_SERVICE_URL set → POST real midnight_service /prove
                       with private circuit inputs (_map_to_circuit_inputs):
                       python_years, has_postgresql, has_aws_cert,
                       has_bachelors_or_equivalent (private) +
                       required_python_years, require_postgresql,
                       require_aws_cert, require_bachelors (public)
                       — falls back to the mock on any failure
           │
           └─→ ApplicationResult stored & returned:
                 { candidate_ref, job_id, match, proof,
                   disclosure_level: "anonymous", contact: null }


3. EMPLOYER VIEWS APPLICANTS
   Employer
     │
     └─→ GET /api/employers/jobs/{job_id}/candidates
           │
           └─→ every ApplicationResult for that job, contact stripped
                 unless disclosure_level == "full_disclosure"


4. CANDIDATE DISCLOSES (their choice, per application)
   Client
     │
     └─→ POST /api/candidates/{id}/disclose/{job_id}?level=full_disclosure
           │
           └─→ candidate.disclosure_level updated;
                 application.contact populated {name, email, phone}
                 (only for this one job_id — other applications from the
                 same candidate are untouched)
```

---

## Rules engine algorithm

```
Input: JobRequirements + ExtractionResult
       ↓

┌───────────────────────────────────────┐
│  SKILL MATCHING                        │
├───────────────────────────────────────┤
│ Required: {"python": 3, "postgresql": 0,│
│            "aws": 0, "backend": 0}      │
│                                         │
│ Candidate has: {"python": 4,           │
│   "postgresql": 0, "aws": 0,           │
│   "backend": 4, "fastapi": 0, ...}     │
│                                         │
│ Result: all 4 satisfied (python 4>=3,  │
│ others just need to be present)        │
└───────────────────────────────────────┘
       ↓
┌───────────────────────────────────────┐
│  CERTIFICATION MATCHING                │
├───────────────────────────────────────┤
│ Required: ["aws_certified"]            │
│ Candidate has: ["aws_certified"]  ✓    │
└───────────────────────────────────────┘
       ↓
┌───────────────────────────────────────┐
│  EDUCATION MATCHING                    │
├───────────────────────────────────────┤
│ Required: "bachelors" or higher        │
│ Candidate has: "bachelors"  ✓          │
│ ("equivalent_experience" always passes)│
└───────────────────────────────────────┘
       ↓
┌───────────────────────────────────────┐
│  SCORE + TIER                          │
├───────────────────────────────────────┤
│ Criteria checked: 6 (4 skills + 1 cert │
│  + 1 education)                        │
│ Criteria satisfied: 6                  │
│ score = 6/6 = 1.0                      │
│ all satisfied → tier = "excellent"     │
│ overall_match = true                   │
└───────────────────────────────────────┘

Output: MatchResult
```

---

## Tier interpretation

```
┌───────────────────────────────────────────────────────────┐
│ TIER            SCORE RANGE       MEANING                  │
├───────────────────────────────────────────────────────────┤
│ excellent   │ all criteria met │ Meets every requirement.  │
│ good        │ score >= 0.75    │ Meets most requirements.  │
│ average     │ score >= 0.5     │ Meets about half.         │
│ poor        │ below 0.5        │ Missing most requirements.│
└───────────────────────────────────────────────────────────┘

overall_match is only ever true at "excellent" — it requires every
criterion satisfied, not just a high score.
```

---

## Error handling

```
POST /api/candidates
    ├─→ neither file nor cv_text given, or both given → 422
    ├─→ non-PDF filename, empty file, invalid PDF signature → 422
    ├─→ PDF has no extractable text (e.g. scanned image) → 422
    ├─→ ai_service unreachable → 502
    ├─→ ai_service returns an unexpected shape → 502
    └─→ success → 200 CandidateProfile (PII/extraction excluded)

POST /api/candidates/{id}/apply/{job_id}
    ├─→ unknown candidate_id or job_id → 404
    └─→ success → 200 ApplicationResult (Midnight failure never surfaces
          as an error here — midnight_client falls back to the mock)

POST /api/candidates/{id}/disclose/{job_id}
    ├─→ unknown candidate_id → 404
    ├─→ no prior application for that job (must /apply first) → 404
    └─→ success → 200 ApplicationResult, contact populated iff full_disclosure

GET /api/jobs/{job_id}, GET /api/employers/jobs/{id}/candidates
    └─→ unknown job_id → 404
```

---

## Storage (in-memory)

```
Jobs table (database.py: db.jobs)
┌─────────┬────────────────────┬──────────┬──────────────┐
│ job_id  │ title              │ domain   │ is_active    │
├─────────┼────────────────────┼──────────┼──────────────┤
│job-001  │Backend Engineer    │example-…│true          │
│job-002  │Sr Backend Engineer │northwind-…│true          │
│job-003  │"URGENT" (unverified)│unknown…│true          │
└─────────┴────────────────────┴──────────┴──────────────┘

Candidates table (db.candidates)
┌──────────────┬───────────────┬─────────────────┬──────────────────┐
│ candidate_id │ anonymized_ref│ extraction (priv)│ disclosure_level │
├──────────────┼───────────────┼─────────────────┼──────────────────┤
│uuid-...      │PX-101         │{skills:{...}}    │anonymous         │
└──────────────┴───────────────┴─────────────────┴──────────────────┘

Applications table (db.applications), keyed by (candidate_id, job_id)
┌──────────────┬────────┬───────────┬─────────┬───────────────────┐
│ candidate_id │ job_id │ match     │ proof   │ contact           │
├──────────────┼────────┼───────────┼─────────┼───────────────────┤
│uuid-...      │job-001 │{tier:...} │{...}    │null until disclose│
└──────────────┴────────┴───────────┴─────────┴───────────────────┘
```

All three tables reset when `python main.py` restarts — see README's
Future Enhancements for swapping this for a real database.

---

## API response examples

### Candidate registration response
```json
{
  "candidate_id": "3014b969-cff3-439d-8945-219b7981a40d",
  "anonymized_ref": "PX-101",
  "cv_source": "pdf",
  "disclosure_level": "anonymous"
}
```

### Application response (before disclosure)
```json
{
  "candidate_ref": "PX-101",
  "job_id": "job-001",
  "match": {
    "candidate_ref": "PX-101",
    "job_id": "job-001",
    "criteria": [
      {"criterion": "python", "required": ">= 3 years", "satisfied": true},
      {"criterion": "postgresql", "required": "present", "satisfied": true},
      {"criterion": "aws_certified", "required": "present", "satisfied": true},
      {"criterion": "education", "required": "bachelors or higher (or equivalent experience)", "satisfied": true}
    ],
    "score": 1.0,
    "tier": "excellent",
    "overall_match": true
  },
  "proof": {
    "proof_id": "0366053e-...",
    "verified": true,
    "claim": "candidate PX-101 scores excellent (100%) against requirements for job-001",
    "claim_hash": "cd9dbdce...",
    "generated_at": "2026-08-30T11:08:33.218286+00:00"
  },
  "disclosure_level": "anonymous",
  "contact": null
}
```

### After `disclose(level=full_disclosure)`
```json
{
  "...": "...same as above, plus:",
  "disclosure_level": "full_disclosure",
  "contact": {"name": "Jordan Ellis", "email": "jordan@example.com", "phone": "555-1234"}
}
```

---

## Deployment architecture (future)

```
┌─────────────────────────────────────────────────────────────────┐
│  User devices (browser)                                          │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React/Next.js)                                        │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ API calls
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend/ (FastAPI) — Docker container, auto-scaling             │
└───────┬──────────────────────┬──────────────────────┬────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────────┐   ┌───────────────────────┐
│ ai_service/   │    │ Database          │   │ midnight_service/      │
│ (Claude calls)│    │ (Postgres/Mongo,  │   │ (real Midnight ZK      │
│               │    │  replacing        │   │  proofs — not yet      │
│               │    │  database.py)     │   │  compiled/deployed)    │
└──────────────┘    └──────────────────┘   └───────────────────────┘
```

This completes the VeriHire architecture overview.
