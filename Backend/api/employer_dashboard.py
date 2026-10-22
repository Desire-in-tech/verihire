from fastapi import APIRouter, Depends, HTTPException

from Backend.auth import require_employer
from Backend.database import db
from Backend.employer_results import public_employer_results
from Backend.models import Job, JobListResponse

router = APIRouter(prefix="/api/employer", tags=["employer-dashboard"])


def _owned_upload(upload_id: str, employer_id: str) -> dict:
    try:
        upload = db.get_cv_upload(upload_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc
    if upload.get("employer_id") != employer_id:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


def _jobs_by_id(employer_id: str) -> dict:
    return {job.job_id: job for job in db.list_jobs_for_employer(employer_id)}


@router.get("/jobs", response_model=JobListResponse, summary="Get this employer's jobs")
async def get_jobs(employer: dict = Depends(require_employer)):
    jobs = db.list_jobs_for_employer(employer["employer_id"])
    return JobListResponse(jobs=jobs, total_count=len(jobs))


@router.get("/jobs/{job_id}", response_model=Job, summary="Get job details")
async def get_job_details(job_id: str, employer: dict = Depends(require_employer)):
    try:
        job = db.get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    if db.get_job_owner(job_id) != employer["employer_id"]:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/results", summary="List stored Midnight verification results")
async def list_employer_results(employer: dict = Depends(require_employer)):
    employer_id = employer["employer_id"]
    uploads = db.list_uploads_for_employer(employer_id)
    return {"results": public_employer_results(uploads, _jobs_by_id(employer_id))}


@router.get("/proof-result/{upload_id}", summary="Get proof result for CV upload")
async def get_proof_result(upload_id: str, employer: dict = Depends(require_employer)):
    upload = _owned_upload(upload_id, employer["employer_id"])
    rows = public_employer_results([upload], _jobs_by_id(employer["employer_id"]))
    if not rows:
        raise HTTPException(status_code=404, detail="No proof results found for this upload")
    return {
        "upload_id": upload_id,
        "proof_results": [
            {
                "job_id": row["job_id"],
                "applicant_verified": row["applicant_verified"],
                "proof_data": row["proof_data"],
                "matching_result": {
                    "job_id": row["job_id"],
                    "matches": row["matches"],
                    "score": row["match_score"],
                },
            }
            for row in rows
        ],
    }


@router.get("/matching-summary/{upload_id}", summary="Get matching summary for CV")
async def get_matching_summary(upload_id: str, employer: dict = Depends(require_employer)):
    upload = _owned_upload(upload_id, employer["employer_id"])
    summary = []
    for result in upload.get("matching_results", []):
        if not isinstance(result, dict):
            continue
        job_id = result.get("job_id")
        if not isinstance(job_id, str):
            continue
        try:
            job = db.get_job(job_id)
        except ValueError:
            continue
        if db.get_job_owner(job_id) != employer["employer_id"]:
            continue
        score = result.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            score = None
        matches = result.get("matches")
        summary.append(
            {
                "job_id": job_id,
                "job_title": job.title,
                "company": job.company,
                "matches": matches if isinstance(matches, bool) else None,
                "score": score,
            }
        )
    summary.sort(key=lambda item: (item["score"] is not None, item["score"] or 0), reverse=True)
    return {
        "upload_id": upload_id,
        "total_jobs": len(summary),
        "matched_jobs": sum(1 for item in summary if item["matches"]),
        "matches": summary,
    }
