# VeriHire — Shared Schema Contract

This is the one document both people on the backend/AI side should agree on
**before** writing more code. It exists because the AI extraction service and
the backend/API service are two separate FastAPI apps that only talk to each
other over HTTP + JSON — if the field names or types drift between them,
Pydantic will validate happily on both ends while the actual connection
silently breaks.

If you change any shape below, update this file in the same commit and tell
your teammate.

## 1. Candidate credentials — `ExtractionResult`

Produced by the AI service (`POST /extract`), consumed by the backend.

| field              | type                  | notes                                                            |
|--------------------|-----------------------|-------------------------------------------------------------------|
| `skills`           | `dict[str, int]`      | skill name (lowercase) → years of experience. `0` = "has it, no specific duration". |
| `certifications`   | `list[str]`           | lowercase certification names, e.g. `"aws_certified"`.          |
| `education_level`  | `str`                 | one of: `"none"`, `"highschool"`, `"bachelors"`, `"masters"`, `"phd"`, `"equivalent_experience"`. |
| `raw_summary`      | `str \| null`         | 1-2 sentence AI summary of the candidate, optional, for internal debugging/display only — never shown to an employer before full disclosure. |

Example:

```json
{
  "skills": {"python": 4, "postgresql": 2, "backend": 4},
  "certifications": ["aws_certified"],
  "education_level": "bachelors",
  "raw_summary": "Backend engineer with 4 years Python experience."
}
```

This generalizes the toy example in the original tools doc
(`python_years_experience`, `postgresql_experience`, `aws_certified` as three
hardcoded fields). A flexible `skills` dict scales to any job's requirements
without hardcoding a field per skill — important since the seed data has
several different jobs with different requirements. If you'd rather keep the
original hardcoded-fields version for simplicity, that's a five-minute change
in `models.py` on both sides — just make it in both places at once.

## 2. Job requirements — `JobRequirements`

Produced by the AI service (`POST /parse-job`) from a free-text job
description, consumed by the backend's rules engine.

| field                     | type             | notes                                   |
|---------------------------|------------------|------------------------------------------|
| `required_skills`         | `dict[str, int]` | skill name → minimum years required. `0` = must simply be present. |
| `required_certifications` | `list[str]`      | certifications the candidate must have. |
| `min_education_level`     | `str \| null`    | same enum as above, or `null` for no requirement. |

## 3. Match result — `CriterionResult` / `MatchResult`

Produced by the backend's rules engine (`rules_engine.py`), never by the AI.
This is the part of the architecture that is explicit, deterministic code —
not an AI judgment call — per the "AI extracts, rules decide, Midnight
verifies" principle in the pitch doc.

```json
{
  "candidate_ref": "PX-104",
  "job_id": "job-001",
  "criteria": [
    {"criterion": "python", "required": ">= 3 years", "satisfied": true},
    {"criterion": "postgresql", "required": "present", "satisfied": true},
    {"criterion": "aws_certified", "required": "present", "satisfied": true},
    {"criterion": "education", "required": "bachelors or equivalent_experience", "satisfied": true}
  ],
  "score": 1.0,
  "tier": "excellent",
  "overall_match": true
}
```

`candidate_ref` is an anonymized reference (e.g. `PX-104`), never the
candidate's name or ID. This is what an employer is allowed to see before any
disclosure step.

`score` is the fraction of criteria satisfied (0.0-1.0); `tier` is the
graded label the employer UI actually displays - one of `"excellent"`
(all criteria met), `"good"` (score >= 0.75), `"average"` (score >= 0.5),
or `"poor"` (below that). See `backend/app/rules_engine.py`'s
`_tier_for_score` for the exact cutoffs - easy to retune in one place.

## 4. Proof — `ProofResult`

Produced by `midnight_client.py`, which calls either the real Midnight
service (`midnight_service/`, once it's actually deployed and
`MIDNIGHT_SERVICE_URL` is set) or the offline mock (`midnight_mock.py`) if
that service isn't configured or isn't reachable. Same shape either way,
so nothing downstream needs to know which one produced it.

```json
{
  "proof_id": "b4b8f3c2-...",
  "verified": true,
  "claim": "candidate PX-104 satisfies requirements for job-001",
  "claim_hash": "3f9a...",
  "generated_at": "2026-08-29T12:00:00Z"
}
```

## 5. Employer verification — `EmployerVerificationResult`

Produced by `employer_verification.py` (currently a mocked registry lookup).

```json
{
  "company_name": "Example Technologies",
  "domain": "example-technologies.com",
  "company_identity_verified": true,
  "domain_ownership_verified": true,
  "job_posting_authorized": true,
  "recruiter_authorized": true,
  "overall_verified": true
}
```

## Ports (local dev)

- AI extraction service: `http://localhost:8001`
- Backend / API service: `http://localhost:8000`

The backend reads the AI service's URL from `AI_SERVICE_URL` in its `.env`
(see `backend/.env.example`), so this can change without touching code.
