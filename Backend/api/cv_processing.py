from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from Backend.models import (
    CVUploadResponse,
    RulesEngineResult,
    ProofResult,
    ExtractedCVData,
)
from Backend.lmm_agent_client import LMMAgentClient
from Backend.pdf_extractor import extract_text_from_pdf
from Backend.rules_engine import RulesEngine
from Backend.database import db
from Backend.midnight_client import MidnightClient
import uuid

router = APIRouter(prefix="/api", tags=["cv-processing"])
lmm_agent_client = LMMAgentClient()
midnight_client = MidnightClient()


def _build_results(
    extracted_data: ExtractedCVData,
    job_id: Optional[str] = None,
):
    """
    Run the deterministic rules engine.

    If job_id is provided, evaluate only that job.
    Otherwise evaluate all active jobs.
    """
    if job_id:
        job = db.get_job(job_id)
        jobs = [job] if job.is_active else []
    else:
        jobs = [
            job
            for job in db.get_all_jobs()
            if job.is_active
        ]

    matching_results: list[RulesEngineResult] = []
    proof_results: list[ProofResult] = []

    for job in jobs:
        result = RulesEngine.evaluate(
            job.job_id,
            job.criteria,
            extracted_data,
        )

        matching_results.append(result)

        proof_results.append(
            ProofResult(
                job_id=job.job_id,
                applicant_verified=False,
                cv_data=extracted_data,
                matching_result=result,
                proof_data={
                    "status": "pending",
                    "mode": "not_requested",
                },
            )
        )

    return matching_results, proof_results


@router.post(
    "/upload-cv",
    response_model=CVUploadResponse,
    summary="Upload and process a CV (PDF)",
)
async def upload_cv(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
):
    """
    Upload and process a candidate CV.

    The PDF is converted to text locally before the text is sent
    to the AI extraction service.
    """
    try:
        return await _process_cv(
            file=file,
            job_id=job_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CV: {str(exc)}",
        )


@router.post(
    "/upload-cv-pdf",
    response_model=CVUploadResponse,
    summary="Upload and process a CV from PDF",
)
async def upload_cv_pdf(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
):
    """
    Compatibility alias for /upload-cv.

    Both endpoints use the same PDF processing pipeline.
    """
    return await upload_cv(
        file=file,
        job_id=job_id,
    )


@router.get(
    "/cv-upload/{upload_id}",
    response_model=CVUploadResponse,
    summary="Get CV upload result",
)
async def get_cv_upload(upload_id: str):
    """
    Retrieve a previously processed CV result.
    """
    try:
        upload_data = db.get_cv_upload(upload_id)

        return CVUploadResponse(
            upload_id=upload_data["upload_id"],
            cv_source=upload_data.get(
                "cv_source",
                "pdf",
            ),
            extracted_text=upload_data.get(
                "extracted_text"
            ),
            extracted_data=ExtractedCVData(
                **upload_data["extracted_data"]
            ),
            matching_results=[
                RulesEngineResult(**result)
                for result in upload_data[
                    "matching_results"
                ]
            ],
            proof_results=[
                ProofResult(**proof)
                for proof in upload_data[
                    "proof_results"
                ]
            ],
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving upload: {str(exc)}",
        )


async def _process_cv(
    file: UploadFile,
    job_id: Optional[str] = None,
) -> CVUploadResponse:
    """
    Complete CV processing pipeline:

        PDF
          ↓
        local PDF text extraction
          ↓
        AI structured extraction
          ↓
        deterministic rules engine
          ↓
        proof/matching results
          ↓
        database persistence
    """

    # ---------------------------------------------------------------
    # 1. Validate file
    # ---------------------------------------------------------------

    if not file.filename:
        raise ValueError("CV file must have a filename")

    if not file.filename.lower().endswith(".pdf"):
        raise ValueError("CV must be uploaded as a PDF")

    # ---------------------------------------------------------------
    # 2. Read PDF
    # ---------------------------------------------------------------

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise ValueError("Uploaded CV is empty")

    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("CV must be a valid PDF file")

    # ---------------------------------------------------------------
    # 3. Extract text locally
    # ---------------------------------------------------------------

    extracted_text = extract_text_from_pdf(pdf_bytes)

    if not extracted_text or not extracted_text.strip():
        raise ValueError(
            "Could not extract text from the uploaded PDF"
        )

    # ---------------------------------------------------------------
    # 4. Send ONLY text to AI service
    # ---------------------------------------------------------------

    extracted_data = await lmm_agent_client.extract_cv(
        extracted_text
    )

    # ---------------------------------------------------------------
    # 5. Run deterministic matching
    # ---------------------------------------------------------------

    # Create the stable reference before contacting Midnight so the opaque
    # result key is deterministic for this upload/job pair.
    upload_id = str(uuid.uuid4())

    matching_results, proof_results = _build_results(
        extracted_data,
        job_id=job_id,
    )

    # Keep the conventional score and the privacy proof as separate signals.
    # Only the fixed-shape flagship job is sent to the Midnight service.
    for proof_result in proof_results:
        job = db.get_job(proof_result.job_id)
        try:
            proof_data = await midnight_client.prove(
                upload_id=upload_id,
                job=job,
                candidate=extracted_data,
                result=proof_result,
            )
        except RuntimeError as exc:
            proof_data = {
                "status": "unavailable",
                "mode": "local_fallback",
                "message": str(exc),
            }
        proof_result.proof_data = proof_data
        proof_result.applicant_verified = proof_data.get("status") == "verified"

    # ---------------------------------------------------------------
    # 6. Persist result
    # ---------------------------------------------------------------

    upload_data = {
        "upload_id": upload_id,
        "cv_source": "pdf",
        "extracted_text": extracted_text,
        "extracted_data": extracted_data.model_dump(),
        "matching_results": [
            result.model_dump()
            for result in matching_results
        ],
        "proof_results": [
            proof.model_dump()
            for proof in proof_results
        ],
    }

    db.save_cv_upload(upload_data)

    # ---------------------------------------------------------------
    # 8. Return API response
    # ---------------------------------------------------------------

    return CVUploadResponse(
        upload_id=upload_id,
        cv_source="pdf",
        extracted_text=extracted_text,
        extracted_data=extracted_data,
        matching_results=matching_results,
        proof_results=proof_results,
    )
