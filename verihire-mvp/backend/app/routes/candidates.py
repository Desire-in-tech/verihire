"""
What this file does
--------------------
Endpoints for the candidate side of VeriHire:

  POST /candidates                          - register a candidate from a CV
  POST /candidates/{id}/apply/{job_id}      - apply to a job (proof, no PII)
  POST /candidates/{id}/disclose/{job_id}   - progressively reveal more info

This is where the "progressive disclosure" idea from the pitch doc actually
happens:

  1. POST /candidates stores the candidate privately and returns only an
     anonymized reference (e.g. "PX-104") - never the raw CV or contact
     info.
  2. POST /candidates/{id}/apply/{job_id} runs the rules engine and the
     (mocked) Midnight proof, and returns a verified/unverified checklist
     tied to the anonymized ref - still no name, email, or phone.
  3. POST /candidates/{id}/disclose/{job_id} is the candidate explicitly
     opting in to reveal more (their choice, not automatic) - moving from
     "verified_candidate" to "full_disclosure" is what finally releases
     their contact info to that specific employer/job.
"""

from fastapi import APIRouter, HTTPException

from .. import store
from ..ai_client import extract_cv
from ..midnight_client import generate_proof
from ..models import (
    ApplicationResult,
    CandidateProfile,
    CVSubmission,
    DisclosureLevel,
)
from ..rules_engine import evaluate

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateProfile, response_model_exclude={"name", "email", "phone", "extraction"})
def create_candidate(submission: CVSubmission):
    """
    Registers a new candidate. AI #1 extracts structured credentials from
    the CV text; the raw CV text itself is never stored or returned - only
    the structured extraction is kept, and even that is excluded from this
    endpoint's response (response_model_exclude above) since the caller
    only needs the candidate_id + anonymized_ref to continue.
    """
    extraction = extract_cv(submission.cv_text)

    candidate = CandidateProfile(
        candidate_id=store.new_id(),
        anonymized_ref=store.next_anonymized_ref(),
        name=submission.name,
        email=submission.email,
        phone=submission.phone,
        extraction=extraction,
    )
    store.save_candidate(candidate)
    return candidate


@router.post("/{candidate_id}/apply/{job_id}", response_model=ApplicationResult)
def apply_to_job(candidate_id: str, job_id: str):
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    match = evaluate(candidate.anonymized_ref, job_id, candidate.extraction, job.requirements)
    # Pass the raw private extraction + public requirements through, not just
    # the already-computed match - a real Midnight circuit needs to do its
    # own private computation, not rubber-stamp a conclusion Python already
    # reached. See midnight_client.py's docstring for why this matters.
    proof = generate_proof(match, candidate.extraction, job.requirements)

    result = ApplicationResult(
        candidate_ref=candidate.anonymized_ref,
        job_id=job_id,
        match=match,
        proof=proof,
        disclosure_level=candidate.disclosure_level,
    )
    store.save_application(candidate_id, job_id, result)
    return result


@router.post("/{candidate_id}/disclose/{job_id}", response_model=ApplicationResult)
def disclose(candidate_id: str, job_id: str, level: DisclosureLevel):
    """
    The candidate chooses to move up a disclosure stage for one specific
    application. This is an explicit, candidate-initiated action - nothing
    else in the system escalates disclosure automatically.
    """
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    application = store.get_application(candidate_id, job_id)
    if application is None:
        raise HTTPException(status_code=404, detail="No application found - call /apply first")

    candidate.disclosure_level = level
    store.save_candidate(candidate)

    application.disclosure_level = level
    if level == DisclosureLevel.FULL_DISCLOSURE:
        application.contact = {
            "name": candidate.name or "",
            "email": candidate.email or "",
            "phone": candidate.phone or "",
        }
    store.save_application(candidate_id, job_id, application)
    return application
