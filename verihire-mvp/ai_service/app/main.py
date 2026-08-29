"""
What this file does
--------------------
The entry point for the AI extraction service. It's a small FastAPI app
with two endpoints:

  POST /extract     - CV text in, structured candidate credentials out (AI #1)
  POST /parse-job    - job description in, structured requirements out (AI #2)

This file itself has almost no logic - it just validates the incoming
request shape (via models.py) and hands the text off to extraction.py,
which is where the actual AI calls happen. Keeping this file "thin" means
the backend team only ever needs to know about the two routes below and
the JSON shapes in SCHEMA_CONTRACT.md - not how the extraction works
internally.

Run it directly with:  uvicorn app.main:app --reload --port 8001
(run from inside the ai_service/ directory, with its virtualenv active)
"""

from fastapi import FastAPI

from .config import settings
from .models import (
    CVExtractionRequest,
    ExtractionResult,
    JobDescriptionRequest,
    JobRequirements,
)
from .extraction import extract_cv, extract_job_requirements

app = FastAPI(
    title="VeriHire AI Extraction Service",
    description="Turns raw CV text and job descriptions into structured, checkable data.",
)


@app.get("/health")
def health():
    """Simple liveness check, and tells you whether a real API key is configured."""
    return {"status": "ok", "ai_enabled": settings.has_ai, "model": settings.anthropic_model}


@app.post("/extract", response_model=ExtractionResult)
def extract(request: CVExtractionRequest) -> ExtractionResult:
    """AI #1 - private CV/credential extraction. See extraction.extract_cv."""
    return extract_cv(request.cv_text)


@app.post("/parse-job", response_model=JobRequirements)
def parse_job(request: JobDescriptionRequest) -> JobRequirements:
    """AI #2 - job requirement analysis. See extraction.extract_job_requirements."""
    return extract_job_requirements(request.description)
