# VeriHire API - Testing Guide

Complete step-by-step guide for testing the API Layer before frontend integration.

## Prerequisites

- Python 3.9+
- Postman (or curl)
- Person B service running on `http://localhost:8001` (or appropriate endpoint)

## Setup

### Step 1: Install Dependencies

```bash
cd /home/tjhazard/midnight-project/verihire/Backend
pip install -r requirements.txt
```

### Step 2: Start API Server

```bash
python main.py
```

Output should show:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 3: Verify Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

---

## API Testing Scenarios

### Scenario 1: Test Health & Jobs Listing

#### 1.1 Health Check
```bash
curl -X GET http://localhost:8000/health
```

**Expected Response:**
```json
{"status": "healthy"}
```

#### 1.2 Get All Jobs
```bash
curl -X GET http://localhost:8000/api/employer/jobs
```

**Expected Response:**
```json
{
  "jobs": [
    {
      "job_id": "job-001",
      "title": "Senior Python Developer",
      "company": "TechCorp Inc",
      "description": "...",
      "criteria": {
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "min_years_experience": 5,
        ...
      },
      "verification_status": "verified",
      "is_active": true
    },
    ...
  ],
  "total_count": 3
}
```

#### 1.3 Get Specific Job
```bash
curl -X GET http://localhost:8000/api/employer/jobs/job-001
```

**Expected Response:** Single job object

---

### Scenario 2: Strong Candidate (Expected to Match Senior Role)

#### 2.1 Upload CV - Close to Requirements
```bash
curl -X POST http://localhost:8000/api/upload-cv \
  -F "file=@/path/to/alice_cv.pdf" \
  -F "job_id=job-001"
```

**Expected Response:**
- `upload_id`: Generated UUID
- `extracted_data`: Extracted CV information
- `matching_results`: Should show strong match with job-001
  - `matches: true`
  - `score: 90+` 
  - `reasoning: "Excellent match..."`

**Example matching_result for job-001:**
```json
{
  "job_id": "job-001",
  "matches": true,
  "score": 95.5,
  "missing_requirements": [],
  "matched_requirements": [
    "Has required skill: Python",
    "Has required skill: FastAPI",
    "Has required skill: PostgreSQL",
    "Has required skill: Docker",
    "Has 6 years experience (required: 5)",
    "Has Bachelor's in Computer Science"
  ],
  "reasoning": "Excellent match (95.5% match rate). Candidate meets nearly all requirements."
}
```

#### 2.2 Retrieve Upload Results
Save the `upload_id` from the previous response, then:

```bash
curl -X GET "http://localhost:8000/api/cv-upload/{upload_id}"
```

Replace `{upload_id}` with actual ID from 2.1

**Expected:** Full response including extracted data and all matching results

#### 2.3 Get Matching Summary (Dashboard View)
```bash
curl -X GET "http://localhost:8000/api/employer/matching-summary/{upload_id}"
```

**Expected Response:**
```json
{
  "upload_id": "{upload_id}",
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
      "company": "StartupXYZ",
      "matches": false,
      "score": 45.0,
      "missing_requirements": [
        "Missing required skill: JavaScript",
        ...
      ]
    },
    ...
  ]
}
```

---

### Scenario 3: Junior Candidate (Expected NOT to Match Senior Roles)

#### 3.1 Upload Underqualified CV
```bash
curl -X POST http://localhost:8000/api/upload-cv \
  -F "file=@/path/to/charlie_cv.pdf"
```

**Expected Response:**
- `upload_id`: Generated UUID
- `extracted_data`: { skills: ["Python", "Java", "SQL"], years_experience: 2, ... }
- `matching_results`: Should show NO match for job-001
  - `matches: false`
  - `score: <60` (low score)
  - Missing critical requirements

**Expected matching_result for job-001:**
```json
{
  "job_id": "job-001",
  "matches": false,
  "score": 25.0,
  "missing_requirements": [
    "Missing required skill: FastAPI",
    "Missing required skill: PostgreSQL",
    "Missing required skill: Docker",
    "Only has 2 years experience (required: 5)"
  ],
  "matched_requirements": [
    "Has required skill: Python",
    "Has Bachelor's in Computer Science"
  ],
  "reasoning": "Poor match (25.0% match rate). Candidate is missing critical requirements: Missing required skill: FastAPI, Missing required skill: PostgreSQL, Missing required skill: Docker."
}
```

#### 3.2 Verify Summary Shows Poor Match
```bash
curl -X GET "http://localhost:8000/api/employer/matching-summary/{upload_id}"
```

**Expected:** All jobs show low scores and `matches: false`

---

### Scenario 4: Different Role Candidate (Matches Different Job)

#### 4.1 Upload JavaScript Developer CV
```bash
curl -X POST http://localhost:8000/api/upload-cv \
  -F "file=@/path/to/bob_cv.pdf"
```

**Expected Response:**
- Should match job-002 with 80%+ score
- Should NOT match job-001 (wrong tech stack)

#### 4.2 Verify Summary
```bash
curl -X GET "http://localhost:8000/api/employer/matching-summary/{upload_id}"
```

**Expected:** job-002 should be first with highest score

---

### Scenario 5: Data Science Candidate (Niche Match)

#### 5.1 Upload Data Science CV
```bash
curl -X POST http://localhost:8000/api/upload-cv \
  -F "file=@/path/to/diana_cv.pdf"
```

**Expected Response:**
- Should match job-003 with 90%+ score
- Should have low scores for job-001 and job-002

---

## Error Handling Tests

### Test 1: Person B Service Unavailable

If Person B is not running, uploading a CV should return:

```bash
curl -X POST http://localhost:8000/api/upload-cv \
  -F "file=@/path/to/any_cv.pdf"
```

**Expected Error Response (HTTP 500):**
```json
{"detail": "Error processing CV: Failed to call Person B service: ..."}
```

### Test 2: Invalid Upload ID

```bash
curl -X GET http://localhost:8000/api/cv-upload/invalid-id
```

**Expected Response (HTTP 404):**
```json
{"detail": "Upload invalid-id not found"}
```

### Test 3: Invalid Job ID

```bash
curl -X GET http://localhost:8000/api/employer/jobs/invalid-job-id
```

**Expected Response (HTTP 404):**
```json
{"detail": "Job invalid-job-id not found"}
```

---

## Integration Testing with Postman

1. **Import Collection:**
   - Open Postman
   - Click "Import"
   - Select `VeriHire_API_Collection.postman_collection.json`

2. **Set Variables:** (optional for dynamic testing)
   - Create environment with variables
   - `{{upload_id}}` - Will be filled from responses

3. **Run Test Scenarios:**
   - Execute requests in order
   - Verify responses match expected formats

4. **Create Tests:** (in Postman)
   ```javascript
   pm.test("Response is valid", function() {
       pm.response.to.have.status(200);
   });
   
   pm.test("Extracted data structure", function() {
       var jsonData = pm.response.json();
       pm.expect(jsonData).to.have.property('extracted_data');
       pm.expect(jsonData.extracted_data).to.have.property('skills');
   });
   ```

---

## Performance Testing

### Load Testing with Multiple CVs

```bash
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/upload-cv \
    -F "file=@/path/to/test_cv_$i.pdf"
done
```

**Monitor:** Response times should be <1 second per request

---

## Debugging

### Enable Debug Logging

Add to `main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Server Logs

Look for:
- Person B service connection attempts
- Pydantic validation errors
- Rules engine scoring details

### Inspect Database State

In Python REPL:
```python
from database import db
print(db.get_all_jobs())
print(db.cv_uploads)
```

---

## Checklist Before Frontend Integration

- [ ] Health check returns 200
- [ ] Job listing shows 3 jobs
- [ ] CV upload returns upload_id
- [ ] Extracted data matches Person B schema
- [ ] Rules engine correctly identifies strong matches
- [ ] Rules engine correctly rejects poor matches
- [ ] Matching summary properly sorted by score
- [ ] Dashboard endpoints return correct data
- [ ] Error handling works for missing uploads/jobs
- [ ] Person B connection errors handled gracefully
- [ ] Pydantic validation catches invalid schemas

---

## Next Steps

Once all tests pass:
1. Deploy Person A API to production
2. Connect frontend to `/api/upload-cv` endpoint
3. Wire employer dashboard to summary endpoints
4. Integrate Midnight layer for proof generation

