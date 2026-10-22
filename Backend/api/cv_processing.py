from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from Backend.auth import require_employer
from Backend.database import db
from Backend.employer_results import public_employer_results
from Backend.lmm_agent_client import LMMAgentClient
from Backend.midnight_client import MidnightClient, applicant_verified_from_proof, empty_proof
from Backend.models import ExtractedCVData, Job, ProofResult
from Backend.pdf_extractor import extract_text_from_pdf
from Backend.rules_engine import RulesEngine
import uuid

router = APIRouter(prefix="/api", tags=["cv-processing"])
lmm_agent_client = LMMAgentClient()
midnight_client = MidnightClient()

_MAX_CV_BYTES = 2_000_000
_SAFE_ERRORS = {
    "CV file must have a filename",
    "CV must be uploaded as a PDF",
    "Uploaded CV is empty",
    "CV must be a valid PDF file",
    "Could not extract text from the uploaded PDF",
    "CV file exceeds the 2 MB limit",
    "A job_id is required",
    "Job is not active",
    "Job not found",
    "PDF content is empty",
    "Could not extract text from PDF. The PDF may contain scanned images instead of selectable text.",
    "Failed to read PDF.",
}


def apply_proof_to_result(proof_result: ProofResult, proof_data: dict | None) -> bool:
    """Store one Midnight outcome and set applicant_verified from it.

    True only when verification_status is verified and eligible is True.
    """
    proof_result.proof_data = proof_data
    proof_result.applicant_verified = applicant_verified_from_proof(proof_data)
    return proof_result.applicant_verified


def _safe_detail(exc: ValueError) -> str:
    message = str(exc)
    if message in _SAFE_ERRORS:
        return message
    return "The CV could not be processed."


def _candidate_view(upload_id: str, proof_results: list[ProofResult], job) -> dict:
    upload = {
        "upload_id": upload_id,
        "proof_results": [proof.model_dump() for proof in proof_results],
    }
    rows = public_employer_results([upload], {job.job_id: job})
    return {
        "upload_id": upload_id,
        "matching_results": [
            {"job_id": row["job_id"], "matches": row["matches"], "score": row["match_score"]}
            for row in rows
        ],
        "proof_results": [
            {
                "job_id": row["job_id"],
                "applicant_verified": row["applicant_verified"],
                "proof_data": row["proof_data"],
            }
            for row in rows
        ],
    }


@router.get("/jobs", summary="List jobs a candidate can apply to")
async def list_public_jobs():
    jobs = db.list_public_jobs()
    return {"jobs": jobs, "total_count": len(jobs)}


@router.post("/upload-cv", summary="Upload and process a CV (PDF)")
async def upload_cv(
    file: UploadFile = File(...),
    job_id: str | None = Form(None),
):
    try:
        return await _process_cv(file=file, job_id=job_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=_safe_detail(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="CV extraction is unavailable.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="CV processing failed.") from exc


@router.post("/upload-cv-pdf", summary="Upload and process a CV from PDF")
async def upload_cv_pdf(
    file: UploadFile = File(...),
    job_id: str | None = Form(None),
):
    return await upload_cv(file=file, job_id=job_id)


@router.get("/cv-upload/{upload_id}", summary="Get a stored upload for its employer")
async def get_cv_upload(upload_id: str, employer: dict = Depends(require_employer)):
    try:
        upload_data = db.get_cv_upload(upload_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc
    if upload_data.get("employer_id") != employer["employer_id"]:
        raise HTTPException(status_code=404, detail="Upload not found")
    job_id = upload_data.get("job_id")
    if not isinstance(job_id, str):
        raise HTTPException(status_code=404, detail="Upload not found")
    try:
        job = db.get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc
    proofs = []
    for proof in upload_data.get("proof_results", []):
        if isinstance(proof, dict):
            proofs.append(ProofResult.model_validate(proof))
    return _candidate_view(upload_id, proofs, job)


async def _process_cv(file: UploadFile, job_id: str | None = None) -> dict:
    filename = Path(file.filename or "").name
    if not filename:
        raise ValueError("CV file must have a filename")
    if not filename.lower().endswith(".pdf"):
        raise ValueError("CV must be uploaded as a PDF")
    if not job_id or not str(job_id).strip():
        raise ValueError("A job_id is required")
    job_id = str(job_id).strip()

    job = db.get_job(job_id)
    if not job.is_active:
        raise ValueError("Job is not active")
    employer_id = db.get_job_owner(job_id)
    if not employer_id:
        raise ValueError("Job not found")

    pdf_bytes = await file.read(_MAX_CV_BYTES + 1)
    if not pdf_bytes:
        raise ValueError("Uploaded CV is empty")
    if len(pdf_bytes) > _MAX_CV_BYTES:
        raise ValueError("CV file exceeds the 2 MB limit")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("CV must be a valid PDF file")

    extracted_text = extract_text_from_pdf(pdf_bytes)
    if not extracted_text or not extracted_text.strip():
        raise ValueError("Could not extract text from the uploaded PDF")

    extracted_data = await lmm_agent_client.extract_cv(extracted_text)
    upload_id = str(uuid.uuid4())
    matching_results, proof_results = _build_results(extracted_data, job)

    for proof_result in proof_results:
        try:
            proof_data = await midnight_client.prove(
                upload_id=upload_id,
                job=job,
                candidate=extracted_data,
                result=proof_result,
            )
        except RuntimeError:
            proof_data = empty_proof(
                verification_status="unavailable",
                eligible=None,
                message="Midnight verification is unavailable.",
            )
        apply_proof_to_result(proof_result, proof_data)

    db.save_cv_upload(
        {
            "upload_id": upload_id,
            "employer_id": employer_id,
            "job_id": job.job_id,
            "cv_source": "pdf",
            "extracted_text": extracted_text,
            "extracted_data": extracted_data.model_dump(),
            "matching_results": [result.model_dump() for result in matching_results],
            "proof_results": [proof.model_dump() for proof in proof_results],
        }
    )
    return _candidate_view(upload_id, proof_results, job)


def _build_results(extracted_data: ExtractedCVData, job: Job):
    result = RulesEngine.evaluate(job.job_id, job.criteria, extracted_data)
    matching_results = [result]
    proof_results = [
        ProofResult(
            job_id=job.job_id,
            applicant_verified=False,
            cv_data=extracted_data,
            matching_result=result,
            proof_data=empty_proof(
                verification_status=None,
                eligible=None,
                message="Midnight verification has not been requested.",
            ),
        )
    ]
    return matching_results, proof_results
