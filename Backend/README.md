# VeriHire API Layer

This is the API Layer for the VeriHire recruitment verification system. It receives CVs, calls Person B's extraction service, runs a rules engine for job matching, and interfaces with the Midnight layer for zero-knowledge proofs.

## Architecture

```
Frontend (CV Upload)
    ↓
API Layer (FastAPI) ← Person B Service (CV Extraction)
    ↓
Rules Engine (Job Matching)
    ↓
Midnight Layer (ZK Proofs)
    ↓
Employer Dashboard 
```

## Project Structure

```
Backend/
├── main.py                      # FastAPI application entry point
├── config.py                   # Configuration management
├── models.py                   # Pydantic data models
├── database.py                 # In-memory database with seed data
├── rules_engine.py             # Job matching rules engine
├── person_b_client.py          # Client for Person B's service
├── api/
│   ├── __init__.py
│   ├── router.py               # Router aggregation
│   ├── cv_processing.py        # CV upload and processing endpoints
│   └── employer_dashboard.py   # Employer dashboard endpoints
├── data/
│   ├── seed_jobs.json          # Sample jobs with criteria
│   └── seed_cvs.json           # Sample CV data
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── .gitignore
├── VeriHire_API_Collection.postman_collection.json  # Postman test collection
└── README.md
```

## Dependencies

- **FastAPI**: Web framework for building APIs
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and settings management
- **httpx**: Async HTTP client for calling Person B's service

## Setup

### 1. Install Dependencies

```bash
cd Backend
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file if needed:
```
AI_SERVICE_URL=http://localhost:8001
# Leave empty until a compiled contract, proof server, and funded wallet exist.
MIDNIGHT_SERVICE_URL=
```

### 3. Run the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

API documentation will be at `http://localhost:8000/docs` (Swagger UI)

## Features

### 1. CV Upload Endpoint (`POST /api/upload-cv`)

Upload CV as PDF file and:
1. Validates PDF payload format
2. Forwards raw PDF bytes to Person B's LMM agent `/extract` endpoint
3. Validates response with Pydantic
4. Runs rules engine against all jobs
5. Requests a real Midnight proof only when `MIDNIGHT_SERVICE_URL` is configured

**Request (multipart/form-data):**
```
- file: PDF file upload
- job_id: (optional) string
```

### 2. Legacy Alias Endpoint (`POST /api/upload-cv-pdf`) 🆕

This endpoint is retained for backwards compatibility and follows the same multipart PDF contract as `/api/upload-cv`.

**Request (multipart/form-data):**
```
- file: PDF file upload
- job_id: (optional) string
```

**Response includes:**
- `cv_source: "pdf"` - Indicates PDF source
- `extracted_text` - extracted selectable text from the uploaded PDF
- `extracted_data` - Parsed CV data from Person B
- `matching_results` - Job matches with scores
- `proof_results` - Proof verification data

### 2. Rules Engine

The rules engine evaluates CVs against job criteria by checking:

- **Required Skills**: Exact skill match required
- **Years of Experience**: Must meet minimum
- **Education Level**: Soft requirement with flexibility
- **Languages**: Required languages must be present
- **Certifications**: Optional but scored

**Match Score Calculation:**
- 90-100%: Excellent match
- 75-89%: Good match
- 60-74%: Partial match
- <60%: Poor match

### 3. Employer Dashboard Endpoints

#### `GET /api/employer/jobs`
List all active jobs

#### `GET /api/employer/jobs/{job_id}`
Get details for a specific job

#### `GET /api/employer/matching-summary/{upload_id}`
Get a summary of how a CV matches all jobs (sorted by score)

#### `GET /api/employer/proof-result/{upload_id}`
Get proof result from Midnight layer for employer verification

## Seed Data

The system comes with 3 sample jobs and 4 sample CVs:

### Jobs:
1. **job-001**: Senior Python Developer (verified) - Needs 5+ years, Python, FastAPI, PostgreSQL, Docker
2. **job-002**: Full Stack JavaScript Developer (verified) - Needs 3+ years, JavaScript, React, Node.js, AWS
3. **job-003**: Data Science Engineer (unverified) - Needs 4+ years, Python, ML, Statistics, Spark, SQL, Master's degree

### CVs:
1. **Alice Johnson** - 6 years, Python/FastAPI/PostgreSQL/Docker specialist → Matches job-001 (95%+)
2. **Bob Smith** - 4 years, JavaScript/React/Node.js/AWS specialist → Matches job-002 (80%+)
3. **Charlie Davis** - 2 years, junior developer → Poor match for senior roles
4. **Diana Chen** - 5 years, Data Science Master's with ML expertise → Matches job-003 (90%+)

## Testing with Postman

### Import Collection

1. Open Postman
2. Click "Import" → Select `VeriHire_API_Collection.postman_collection.json`
3. The collection will load with pre-configured requests

### Test Flow

1. **Health Check** - Verify API is running
   ```
   GET /health
   ```
   Expected: `{"status": "healthy"}`

2. **Get Jobs** - List available jobs
   ```
   GET /api/employer/jobs
   ```

3. **Upload CV** - Test CV processing (3 test cases included)
   ```
   POST /api/upload-cv
   ```
   Response will include `upload_id`

4. **Get Results** - Retrieve CV processing results
   ```
   GET /api/cv-upload/{upload_id}
   ```
   Use the `upload_id` from step 3

5. **Get Matching Summary** - Dashboard view of matches
   ```
   GET /api/employer/matching-summary/{upload_id}
   ```

6. **Get Proof Result** - Verification results
   ```
   GET /api/employer/proof-result/{upload_id}
   ```

### Test Cases

**Test 1: Strong Match**
- Upload Senior Python Developer CV
- Should match job-001 with 95%+ score
- All required skills present

**Test 2: Poor Match**
- Upload Junior Developer CV
- Should not match job-001
- Missing years of experience and skills

**Test 3: Good Match**
- Upload Full Stack JS CV
- Should match job-002 with 80%+ score
- Some optional requirements missing

## Integration Points

### Person B Service Integration

The API calls Person B's LMM `/extract` endpoint with multipart PDF payload:

```python
async def extract_cv_from_pdf(pdf_content: bytes, filename: str = "cv.pdf") -> ExtractedCVData:
    response = await client.post(
        f"{LMM_AGENT_URL}/extract",
        files={"cv_pdf": (filename, pdf_content, "application/pdf")}
    )
    return ExtractedCVData(**response.json())  # Validated with Pydantic
```

**Expected Response Schema from Person B:**
```json
{
  "skills": ["Python", "FastAPI"],
  "years_experience": 6,
  "education_level": "Bachelor's in Computer Science",
  "languages": ["English"],
  "certifications": []
}
```

### Midnight Layer Integration

The API sends only the fixed-shape circuit inputs needed by `job-001` to the
Node Midnight service. When that service is not configured or unavailable, the
response is explicitly marked `not_configured`, `unsupported_job`, or
`unavailable`; it is never marked verified.

## API Documentation

Once running, access the interactive API docs at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Common Issues

### Person B Service Connection Error
- Check that Person B/LMM agent is running on the configured URL
- Verify `/extract` endpoint accepts multipart PDF uploads (`cv_pdf` file field)

### Pydantic Validation Error
- Ensure Person B returns exactly the schema defined in `models.ExtractedCVData`
- Check for extra/missing fields or incorrect types

### Upload ID Not Found
- Verify the upload_id is correct and matches from the upload response
- Upload data is stored in-memory, so it's lost on server restart

## Future Enhancements

- [ ] Persistent database (PostgreSQL/MongoDB)
- [ ] Real Midnight layer integration for ZK proofs
- [ ] Job criteria versioning
- [ ] Detailed audit logs
- [ ] Batch CV processing
- [ ] Advanced rules engine with weighted criteria
- [ ] Admin API for managing jobs

## Development

To modify the rules engine, edit [rules_engine.py](rules_engine.py):

```python
@staticmethod
def evaluate(job_id: str, job_criteria: JobCriteria, cv_data: ExtractedCVData) -> RulesEngineResult:
    # Add custom logic here
```

To add new jobs, edit [data/seed_jobs.json](data/seed_jobs.json) or use a database migration.

## License

Part of the VeriHire project.
