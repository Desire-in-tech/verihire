# VeriHire Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                         FRONTEND (React)                         │
│                    - CV Upload Form                              │
│                    - Jobs Dashboard                              │
│                    - Match Results View                          │
│                                                                 │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP
                                 ▼
     ┌─────────────────────────────────────────────────┐
     │                                                 │
     │         PERSON A: API LAYER (This Project)       │
     │                    FastAPI                       │
     │                                                 │
     │  ┌────────────────────────────────────────┐    │
     │  │      API Endpoints                     │    │
     │  ├────────────────────────────────────────┤    │
     │  │ POST   /api/upload-cv                  │    │
     │  │ GET    /api/cv-upload/{id}             │    │
     │  │ GET    /api/employer/jobs              │    │
     │  │ GET    /api/employer/jobs/{id}         │    │
     │  │ GET    /api/employer/matching-summary  │    │
     │  │ GET    /api/employer/proof-result      │    │
     │  └────────────────────────────────────────┘    │
     │                        ▼                        │
     │  ┌────────────────────────────────────────┐    │
     │  │    CV Processing Pipeline              │    │
     │  ├────────────────────────────────────────┤    │
     │  │ 1. Parse CV text                       │    │
     │  │ 2. Call Person B /extract endpoint    │    │
     │  │ 3. Validate with Pydantic             │    │
     │  │ 4. Run Rules Engine                    │    │
     │  │ 5. Generate Proof Results              │    │
     │  └────────────────────────────────────────┘    │
     │                        ▼                        │
     │  ┌────────────────────────────────────────┐    │
     │  │    Data Storage (In-Memory Database)   │    │
     │  ├────────────────────────────────────────┤    │
     │  │ - Jobs (3 seed items)                 │    │
     │  │ - CV Uploads (temporary storage)      │    │
     │  └────────────────────────────────────────┘    │
     │                                                 │
     └─────┬─────────────────────────────────────┬────┘
           │ HTTP (Person B)                     │ HTTP (Midnight)
           ▼                                     ▼
    ┌────────────────────┐               ┌──────────────────┐
    │  PERSON B SERVICE  │               │  MIDNIGHT LAYER  │
    │ (CV Extraction)    │               │  (ZK Proofs)     │
    │                    │               │                  │
    │ POST /extract      │               │ POST /generate   │
    │ Input: CV text     │               │ Input: Proof req │
    │ Output: Structured │               │ Output: Proof    │
    │         CV data    │               │                  │
    └────────────────────┘               └──────────────────┘
```

---

## Data Flow Diagram

```
1. CV UPLOAD
   Frontend
     │
     └─→ POST /api/upload-cv {"cv_text": "..."}
           │
           ▼
   API Layer receives CV
     │
     └─→ Generate upload_id


2. CV EXTRACTION
   API Layer
     │
     └─→ PersonBClient.extract_cv(cv_text)
           │
           └─→ HTTP POST to Person B /extract
                 │
                 ▼
              Person B Service
                 │
                 └─→ Structured extraction
                     {
                       "skills": [...],
                       "years_experience": N,
                       "education_level": "...",
                       ...
                     }
           │
           └─→ Validate with Pydantic
                 │
                 └─→ ExtractedCVData model


3. RULES ENGINE EVALUATION
   API Layer
     │
     └─→ For each active job:
           │
           ├─→ RulesEngine.evaluate(job_criteria, cv_data)
           │     │
           │     ├─→ Check required skills
           │     ├─→ Check experience level
           │     ├─→ Check education
           │     ├─→ Check languages
           │     ├─→ Check certifications
           │     │
           │     └─→ Calculate score & generate result
           │
           └─→ RulesEngineResult


4. PROOF GENERATION
   API Layer
     │
     └─→ Create ProofResult for each job
           │
           ├─→ job_id
           ├─→ applicant_verified (from job.verification_status)
           ├─→ cv_data (extracted)
           ├─→ matching_result (from rules engine)
           └─→ proof_data (placeholder for Midnight)


5. RESPONSE & STORAGE
   API Layer
     │
     ├─→ Save to database (cv_uploads)
     │
     └─→ Return CVUploadResponse
           │
           ├─→ upload_id
           ├─→ extracted_data
           ├─→ matching_results[]
           └─→ proof_results[]


6. DASHBOARD ACCESS
   Frontend/Employer
     │
     ├─→ GET /api/employer/matching-summary/{upload_id}
     │     │
     │     └─→ Sorted by score, ready for display
     │
     └─→ GET /api/employer/proof-result/{upload_id}
           │
           └─→ Proof verification data
```

---

## Component Interaction

```
┌──────────────────┐
│     main.py      │  ← Entry point, FastAPI setup
└────────┬─────────┘
         │
    ┌────┴─────────────────────────────────┐
    │                                      │
    ▼                                      ▼
┌──────────────────┐        ┌──────────────────┐
│  config.py       │        │  database.py     │
│ Settings from    │        │ In-memory storage│
│ .env file        │        │ + seed data      │
└──────────────────┘        └──────────────────┘
    ▲                            ▲
    │                            │
    └────────────┬───────────────┘
                 │
    ┌────────────▼─────────────┐
    │      models.py           │  ← Pydantic schemas
    │  (8 data models)         │
    └────────────┬─────────────┘
                 │
    ┌────────────▼─────────────────────────────┐
    │                                          │
    │   ┌──────────────────────────────────┐  │
    │   │  api/cv_processing.py            │  │
    │   │  - POST /upload-cv               │  │
    │   │  - GET  /cv-upload/{id}          │  │
    │   └──────────┬───────────────────────┘  │
    │              │                          │
    │              ├─→ PersonBClient ────────→ Person B Service
    │              │                          (Extract CV)
    │              ├─→ RulesEngine           
    │              │   (Match CV to jobs)     
    │              │                          │
    │   ┌──────────▼───────────────────────┐  │
    │   │  api/employer_dashboard.py       │  │
    │   │  - GET /employer/jobs            │  │
    │   │  - GET /employer/matching-summary│  │
    │   │  - GET /employer/proof-result    │  │
    │   └──────────────────────────────────┘  │
    │                                          │
    │            (routes aggregated)           │
    │                                          │
    └──────────────────────────────────────────┘
```

---

## Rules Engine Algorithm

```
Input: Job Criteria + Extracted CV Data
       ↓

┌─────────────────────────────────────┐
│  SKILL MATCHING                     │
├─────────────────────────────────────┤
│ Required: ["Python", "FastAPI",     │
│            "PostgreSQL", "Docker"]  │
│                                     │
│ CV Has: ["Python", "FastAPI",       │
│         "PostgreSQL", "Docker",     │
│         "Linux", "Git"]             │
│                                     │
│ Result: 4/4 skills matched ✓        │
└─────────────────────────────────────┘
       ↓

┌─────────────────────────────────────┐
│  EXPERIENCE MATCHING                │
├─────────────────────────────────────┤
│ Required: 5+ years                  │
│ CV Has: 6 years                     │
│                                     │
│ Result: 6 >= 5 ✓                    │
└─────────────────────────────────────┘
       ↓

┌─────────────────────────────────────┐
│  EDUCATION & OTHER CRITERIA         │
├─────────────────────────────────────┤
│ Required education: Bachelor's      │
│ CV Has: Bachelor's in CS ✓          │
│                                     │
│ Required languages: English         │
│ CV Has: English, Spanish ✓          │
│                                     │
│ Certifications: Optional            │
│ CV Has: AWS, Docker ✓               │
└─────────────────────────────────────┘
       ↓

┌─────────────────────────────────────┐
│  SCORE CALCULATION                  │
├─────────────────────────────────────┤
│ Total Criteria: 7                   │
│ Met Criteria: 7                     │
│                                     │
│ Score = (7 / 7) × 100 = 100%       │
└─────────────────────────────────────┘
       ↓

┌─────────────────────────────────────┐
│  DECISION                           │
├─────────────────────────────────────┤
│ Matches: true                       │
│ Score: 100%                         │
│ Level: "Excellent match"            │
│                                     │
│ Reasoning: "Candidate meets         │
│  nearly all requirements"           │
└─────────────────────────────────────┘

Output: RulesEngineResult
```

---

## Match Score Interpretation

```
┌─────────────────────────────────────────────────────────┐
│ SCORE RANGES & MEANINGS                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  90-100% │ ▓▓▓▓▓▓▓▓░░  EXCELLENT MATCH                 │
│          │            → Candidate meets nearly all    │
│          │              requirements. Proceed with     │
│          │              interest.                      │
│          │                                             │
│  75-89%  │ ▓▓▓▓▓▓░░░░  GOOD MATCH                      │
│          │            → Candidate meets most key      │
│          │              requirements. Consider for     │
│          │              interviews.                    │
│          │                                             │
│  60-74%  │ ▓▓▓▓░░░░░░  PARTIAL MATCH                  │
│          │            → Candidate meets some          │
│          │              requirements. May need         │
│          │              training in some areas.       │
│          │                                             │
│  <60%    │ ▓░░░░░░░░░  POOR MATCH                     │
│          │            → Candidate missing critical    │
│          │              requirements. Not             │
│          │              recommended.                   │
│          │                                             │
└─────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
Upload CV
    │
    ├─→ Person B Connection Error
    │   └─→ Return 500: "Failed to call Person B service"
    │
    ├─→ Invalid Response Schema
    │   └─→ Return 422: "Invalid response schema from Person B"
    │
    ├─→ Invalid Upload ID
    │   └─→ Return 404: "Upload X not found"
    │
    ├─→ Invalid Job ID
    │   └─→ Return 404: "Job X not found"
    │
    └─→ Success
        └─→ Return 200 with CVUploadResponse
```

---

## Database Schema (In-Memory)

```
Jobs Table:
┌──────────┬──────────────────────┬─────────────┬──────┐
│ job_id   │ title                │ verification│active│
├──────────┼──────────────────────┼─────────────┼──────┤
│job-001   │Senior Python Dev     │verified     │true  │
│job-002   │JS Full Stack Dev     │verified     │true  │
│job-003   │Data Science Engineer │unverified   │true  │
└──────────┴──────────────────────┴─────────────┴──────┘

CV Uploads Table:
┌────────────────────┬─────────┬──────────┬──────────┐
│upload_id           │extracted│matching_ │proof_    │
│                    │data     │results   │results   │
├────────────────────┼─────────┼──────────┼──────────┤
│uuid-1234-5678-9012 │{...data}│[results] │[proofs]  │
│uuid-9876-5432-1098 │{...data}│[results] │[proofs]  │
└────────────────────┴─────────┴──────────┴──────────┘
```

---

## API Response Examples

### Upload CV Response
```json
{
  "upload_id": "abc-123-def-456",
  "extracted_data": {
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "years_experience": 6,
    "education_level": "Bachelor's in Computer Science",
    "languages": ["English", "Spanish"],
    "certifications": ["AWS"]
  },
  "matching_results": [
    {
      "job_id": "job-001",
      "matches": true,
      "score": 95.5,
      "missing_requirements": [],
      "matched_requirements": ["Has required skill: Python", ...],
      "reasoning": "Excellent match (95.5% match rate)..."
    }
  ],
  "proof_results": [...]
}
```

### Matching Summary Response
```json
{
  "upload_id": "abc-123-def-456",
  "total_jobs": 3,
  "matched_jobs": 1,
  "matches": [
    {
      "job_id": "job-001",
      "job_title": "Senior Python Developer",
      "company": "TechCorp Inc",
      "matches": true,
      "score": 95.5,
      "reasoning": "Excellent match...",
      "missing_requirements": []
    },
    {
      "job_id": "job-002",
      "job_title": "Full Stack JavaScript Developer",
      "matches": false,
      "score": 15.0,
      "reasoning": "Poor match...",
      "missing_requirements": ["Missing required skill: JavaScript", ...]
    }
  ]
}
```

---

## Deployment Architecture (Future)

```
┌─────────────────────────────────────────────────────────┐
│  User Devices (Browser)                                 │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTPS
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Frontend (React/Next.js)                               │
│  - Hosted on CDN or server                              │
└──────────────────┬──────────────────────────────────────┘
                   │ API Calls
                   ▼
┌─────────────────────────────────────────────────────────┐
│  API Server (FastAPI - Person A)                        │
│  - Docker container                                     │
│  - Kubernetes or serverless                             │
│  - Auto-scaling enabled                                │
└──────────────────┬──────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌────────┐   ┌────────┐   ┌────────────┐
│Person B│   │Database│   │Midnight    │
│(CV     │   │(Postgres│   │Layer       │
│Extract)│   │or Mongo)│   │(ZK Proofs) │
└────────┘   └────────┘   └────────────┘
```

This completes the VeriHire API Layer architecture! 🎉
