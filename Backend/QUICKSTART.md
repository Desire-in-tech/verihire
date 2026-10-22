# VeriHire API Layer - Quick Start

## 5-Minute Setup

```bash
# 1. Navigate to Backend directory
cd /home/tjhazard/midnight-project/verihire/Backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API server
python main.py
```

API runs at: `http://localhost:8000`

## Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Get jobs
curl http://localhost:8000/api/employer/jobs

# Upload CV (minimal)
curl -X POST http://localhost:8000/api/upload-cv \
  -F "file=@/path/to/cv.pdf" \
  -F "job_id=job-001"
```

## Features Implemented ✓

### Core API Components
- ✓ FastAPI application structure
- ✓ Pydantic models for all data types
- ✓ Configuration management with dotenv
- ✓ CORS middleware enabled

### Data Layer
- ✓ In-memory database with seed data
- ✓ 3 sample jobs with detailed criteria (verified/unverified)
- ✓ 4 sample CVs for testing all scenarios

### CV Processing (`POST /api/upload-cv`)
- ✓ Receives CV PDF uploads from frontend
- ✓ Calls Person B/LMM `/extract` endpoint with multipart PDF payload
- ✓ Validates response with Pydantic
- ✓ Returns extracted data with all fields

### Rules Engine
- ✓ Compares CV against job criteria
- ✓ Checks: skills, experience, education, languages, certifications
- ✓ Calculates match score (0-100%)
- ✓ Generates human-readable reasoning
- ✓ Returns pass/fail decision for each job

### Employer Dashboard (`/api/employer/*`)
- ✓ `GET /jobs` - List all active jobs
- ✓ `GET /jobs/{job_id}` - Get job details
- ✓ `GET /matching-summary/{upload_id}` - Dashboard view sorted by match score
- ✓ `GET /proof-result/{upload_id}` - Proof data from Midnight layer

### Testing
- ✓ Postman collection with 8+ scenarios
- ✓ Comprehensive testing guide (TESTING_GUIDE.md)
- ✓ Error handling and edge cases
- ✓ Test data scenarios:
  - Strong match (95%+)
  - Poor match (<25%)
  - Different role match
  - Data science specialist

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| POST | `/api/upload-cv` | Upload and process CV PDF |
| POST | `/api/upload-cv-pdf` | Legacy alias for CV PDF upload |
| GET | `/api/cv-upload/{id}` | Get upload results |
| GET | `/api/employer/jobs` | List all jobs |
| GET | `/api/employer/jobs/{id}` | Get job details |
| GET | `/api/employer/matching-summary/{id}` | CV matches (dashboard) |
| GET | `/api/employer/proof-result/{id}` | Proof verification data |

## Person B Integration

The API expects Person B's `/extract` endpoint to return:

```json
{
  "skills": ["Python", "FastAPI"],
  "years_experience": 6,
  "education_level": "Bachelor's in Computer Science",
  "languages": ["English"],
  "certifications": []
}
```

Configure URL in `.env`:
```
PERSON_B_SERVICE_URL=http://localhost:8001
```

## Documentation

- **API Docs**: `http://localhost:8000/docs` (Swagger)
- **Full README**: [README.md](README.md)
- **Testing Guide**: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Postman Collection**: `VeriHire_API_Collection.postman_collection.json`

## Project Structure

```
Backend/
├── main.py                 ← Entry point (run this)
├── config.py              ← Configuration
├── models.py              ← Pydantic schemas
├── database.py            ← In-memory storage
├── rules_engine.py        ← Job matching logic
├── person_b_client.py     ← Person B service client
├── api/
│   ├── cv_processing.py   ← Upload endpoints
│   └── employer_dashboard.py ← Dashboard endpoints
├── data/
│   ├── seed_jobs.json     ← 3 test jobs
│   └── seed_cvs.json      ← 4 test CVs
└── VeriHire_API_Collection.postman_collection.json ← Postman tests
```

## Next Steps

1. **Start API**: `python main.py`
2. **Test Manually**: Use curl or Postman collection
3. **Verify Person B Integration**: Upload a CV and check extraction
4. **Check Rules Engine**: Verify matching logic with different test cases
5. **Dashboard Testing**: Test employer endpoints with upload results

## Troubleshooting

**Person B Connection Error?**
- Ensure Person B is running on `http://localhost:8001`
- Check `/extract` endpoint is available
- Verify response matches schema in `models.ExtractedCVData`

**Pydantic Validation Error?**
- Check Person B response fields match exactly
- All fields must be present (use empty lists/None for optional)

**Upload Not Found?**
- Data is in-memory only (lost on restart)
- Use correct `upload_id` from response

## Key Files

- [main.py](main.py) - FastAPI app setup
- [models.py](models.py) - Data schemas
- [rules_engine.py](rules_engine.py) - Matching logic
- [api/cv_processing.py](api/cv_processing.py) - CV upload endpoints
- [api/employer_dashboard.py](api/employer_dashboard.py) - Dashboard endpoints
