"""
What this file does
--------------------
Endpoints for the employer/job side of VeriHire:

  GET  /jobs                  - list all job postings (with verification badges)
  GET  /jobs/{job_id}         - fetch one job posting
  POST /jobs                  - employer creates a new job posting
  POST /jobs/verify-external  - check an employer/domain without creating a job

`POST /jobs` is where AI #2 (job requirement analysis) and employer
verification both run: the employer submits a free-text description plus
their company name/domain, this endpoint calls the AI service to turn that
description into structured requirements, calls the (mocked) employer
verification check, and stores the result. Everything a candidate needs to
decide "is this job worth applying to" - verification badges plus
requirements - comes back from GET /jobs before they ever submit a CV.

`POST /jobs/verify-external` supports Scene 1 of the demo: checking a
suspicious job/company that isn't even posted on VeriHire, before deciding
whether to engage with it at all.
"""

from fastapi import APIRouter, HTTPException

from .. import store
from ..ai_client import extract_job_requirements
from ..employer_verification import verify_employer
from ..models import EmployerVerificationResult, JobCreateRequest, JobPosting

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobPosting])
def list_jobs():
    return store.list_jobs()


@router.get("/{job_id}", response_model=JobPosting)
def get_job(job_id: str):
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=JobPosting)
def create_job(request: JobCreateRequest):
    requirements = extract_job_requirements(request.description)
    verification = verify_employer(request.company_name, request.domain)

    job = JobPosting(
        job_id=store.new_id(),
        title=request.title,
        company_name=request.company_name,
        domain=request.domain,
        salary=request.salary,
        description=request.description,
        requirements=requirements,
        verification=verification,
    )
    store.save_job(job)
    return job


@router.post("/verify-external", response_model=EmployerVerificationResult)
def verify_external_employer(company_name: str, domain: str):
    """Check a company/domain that isn't necessarily posted on VeriHire yet."""
    return verify_employer(company_name, domain)
