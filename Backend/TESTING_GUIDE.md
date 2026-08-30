# VeriHire API — Testing Guide

Complete step-by-step guide for testing the candidate registration → apply
→ disclose flow, and the employer job/verification flow, before frontend
integration.

## Prerequisites

- Python 3.10+ (both services use `dict[str, int]`/`X | None` type syntax)
- Postman (or curl)
- Both services running (see [QUICKSTART.md](QUICKSTART.md))

## Setup

```bash
# terminal 1
cd ai_service && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8001

# terminal 2
cd Backend && pip install -r requirements.txt && python main.py
```

```bash
curl http://localhost:8001/health
# {"status": "ok", "ai_enabled": false, "model": "claude-opus-4-5"}
# ai_enabled is false unless ANTHROPIC_API_KEY is set on ai_service — that's fine, offline fallback still works.

curl http://localhost:8000/health
# {"status": "healthy", "jobs_loaded": 3}
```

---

## Scenario 1: Jobs listing and verification badges

### 1.1 List all jobs
```bash
curl http://localhost:8000/api/jobs
```
**Expect**: 3 jobs. `job-001` and `job-002` show `verification.company_identity_verified: true`; `job-003` ("UnknownCompany123") shows every verification flag `false` — this is the deliberately-suspicious seed job.

### 1.2 Get one job
```bash
curl http://localhost:8000/api/jobs/job-001
```
**Expect**: full `JobPosting` including `requirements` (`{"required_skills": {"python": 3, "postgresql": 0, "aws": 0, "backend": 0}, "required_certifications": ["aws_certified"], "min_education_level": "bachelors"}`).

### 1.3 Check an external company before engaging
```bash
curl -X POST "http://localhost:8000/api/jobs/verify-external?company_name=Example%20Technologies&domain=example-technologies.com"
curl -X POST "http://localhost:8000/api/jobs/verify-external?company_name=Sketchy%20Co&domain=totally-legit-i-swear.biz"
```
**Expect**: the first returns all flags `true`; the second (not in the registry) returns all flags `false`.

### 1.4 Post a new job
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Data Engineer",
    "company_name": "Example Technologies",
    "domain": "example-technologies.com",
    "description": "Need 4+ years Python and PostgreSQL, AWS deployment experience. Bachelor'"'"'s required."
  }'
```
**Expect**: 200, with `requirements` populated by `ai_service`'s `/parse-job` extraction and `verification` from the registry (this domain is known-good).

---

## Scenario 2: Strong candidate — text submission

### 2.1 Register from raw text
```bash
curl -X POST http://localhost:8000/api/candidates \
  -F "cv_text=Backend engineer with 4 years of professional Python experience. PostgreSQL and AWS deployment experience. AWS Certified Solutions Architect. Bachelor's degree in Computer Science." \
  -F "name=Jordan Ellis" -F "email=jordan@example.com" -F "phone=555-1234"
```
**Expect**: 200, `{"candidate_id": "...", "anonymized_ref": "PX-1xx", "cv_source": "text", "disclosure_level": "anonymous"}` — no name/email/phone/extraction in the response.

Save `candidate_id`.

### 2.2 Apply to job-001
```bash
curl -X POST http://localhost:8000/api/candidates/{candidate_id}/apply/job-001
```
**Expect**: `match.tier` is `"excellent"` or `"good"`, `match.overall_match` likely `true`, `proof.verified` matching that, and `contact: null`.

### 2.3 Employer view before disclosure
```bash
curl http://localhost:8000/api/employers/jobs/job-001/candidates
```
**Expect**: the application appears with `contact: null`.

### 2.4 Disclose
```bash
curl -X POST "http://localhost:8000/api/candidates/{candidate_id}/disclose/job-001?level=full_disclosure"
```
**Expect**: response now includes `"contact": {"name": "Jordan Ellis", "email": "jordan@example.com", "phone": "555-1234"}`.

### 2.5 Employer view after disclosure
```bash
curl http://localhost:8000/api/employers/jobs/job-001/candidates
```
**Expect**: that same candidate's entry now shows the contact block; any other applicant without disclosure still shows `null`.

---

## Scenario 3: PDF submission

### 3.1 Register from a PDF
```bash
curl -X POST http://localhost:8000/api/candidates \
  -F "file=@/path/to/cv.pdf" -F "name=Alex Rivera"
```
**Expect**: 200, `"cv_source": "pdf"`.

### 3.2 Error cases
```bash
# Non-PDF file
curl -X POST http://localhost:8000/api/candidates -F "file=@/path/to/notes.txt"
# → 422 "File must be a PDF"

# Both file and cv_text given
curl -X POST http://localhost:8000/api/candidates -F "file=@/path/to/cv.pdf" -F "cv_text=hello"
# → 422 "Provide either a PDF file or cv_text, not both"

# Neither given
curl -X POST http://localhost:8000/api/candidates
# → 422 "Provide either a PDF file or cv_text"
```

---

## Scenario 4: Junior / weak-match candidate

### 4.1 Register a thin CV
```bash
curl -X POST http://localhost:8000/api/candidates \
  -F "cv_text=1 year of backend experience, no certifications, no degree."
```

### 4.2 Apply to job-002 (5+ years Python, Docker, Kubernetes required)
```bash
curl -X POST http://localhost:8000/api/candidates/{candidate_id}/apply/job-002
```
**Expect**: `tier` of `"poor"` or `"average"`, `overall_match: false`, several `criteria` entries with `satisfied: false`.

---

## Error handling tests

### Unknown candidate
```bash
curl -X POST http://localhost:8000/api/candidates/does-not-exist/apply/job-001
# → 404 {"detail": "Candidate does-not-exist not found"}
```

### Unknown job
```bash
curl http://localhost:8000/api/jobs/does-not-exist
# → 404 {"detail": "Job does-not-exist not found"}
```

### Disclose before ever applying
```bash
curl -X POST "http://localhost:8000/api/candidates/{candidate_id}/disclose/job-002?level=full_disclosure"
# (assuming this candidate never applied to job-002)
# → 404 {"detail": "No application found for candidate ... on job job-002"}
```

### ai_service unreachable
Stop the `ai_service` process, then:
```bash
curl -X POST http://localhost:8000/api/candidates -F "cv_text=test"
# → 502 {"detail": "AI extraction service unreachable: ..."}
```

---

## Integration testing with Postman

1. Open Postman → Import → `VeriHire_API_Collection.postman_collection.json`.
2. Run scenarios in order: jobs listing → candidate registration → apply → employer view → disclose → employer view again.
3. Save `candidate_id` as a collection variable after registration so later requests can reference it.

---

## Debugging

### Enable debug logging
Add to `main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect in-memory state
```python
from database import db
print(db.get_all_jobs())
print(db.candidates)
print(db.applications)
```

### Check whether ai_service is using real Claude or the offline fallback
```bash
curl http://localhost:8001/health
```
`"ai_enabled": false` means every `/extract`/`/parse-job` call is going
through the offline keyword extractor — expected without
`ANTHROPIC_API_KEY` set, and a common reason extraction looks rougher than
expected.

---

## Checklist before frontend integration

- [ ] Both health checks return 200
- [ ] Job listing shows 3 jobs, with job-003 flagged unverified
- [ ] Candidate registration works via both PDF and raw text
- [ ] Registration response never leaks name/email/phone/extraction
- [ ] Apply returns a sensible tier for a strong vs. weak CV
- [ ] Contact info is `null` until disclosure, and appears only for the disclosed job
- [ ] Employer view respects the same disclosure gating
- [ ] 404s work for unknown candidate/job/application
- [ ] 422s work for malformed candidate registration
- [ ] ai_service-unreachable case returns a clear 502, not a stack trace
