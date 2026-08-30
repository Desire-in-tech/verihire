"""
The view an employer gets of their own job posting: every candidate who
applied, shown as their proof/checklist result - filtered by whatever
disclosure level each candidate has chosen. An employer never sees a
candidate's contact info here unless that specific candidate escalated to
FULL_DISCLOSURE for that specific job (see api/candidates.py).
"""

from fastapi import APIRouter, HTTPException

from database import db
from models import ApplicationResult, DisclosureLevel

router = APIRouter(prefix="/api/employers", tags=["employers"])


@router.get("/jobs/{job_id}/candidates", response_model=list[ApplicationResult])
def list_candidates_for_job(job_id: str):
    try:
        db.get_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = db.list_applications_for_job(job_id)

    # Belt-and-suspenders: strip contact info for anyone below full disclosure,
    # even though disclose() only ever populates it at that level.
    safe_results: list[ApplicationResult] = []
    for r in results:
        if r.disclosure_level != DisclosureLevel.FULL_DISCLOSURE:
            r = r.model_copy(update={"contact": None})
        safe_results.append(r)
    return safe_results
