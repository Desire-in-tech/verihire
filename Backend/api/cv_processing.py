from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from models import (
    CVUploadResponse,
    RulesEngineResult,
    ProofResult,
    ExtractedCVData,
)
from lmm_agent_client import LMMAgentClient
from rules_engine import RulesEngine
from database import db
import uuid

router = APIRouter(prefix="/api", tags=["cv-processing"])
lmm_agent_client = LMMAgentClient()


def _build_results(extracted_data: ExtractedCVData):
    """Run rules engine for all active jobs and return matching/proof results."""
    jobs = db.get_all_jobs()
    matching_results: list[RulesEngineResult] = []
    proof_results: list[ProofResult] = []

    for job in jobs:
        result = RulesEngine.evaluate(job.job_id, job.criteria, extracted_data)
        matching_results.append(result)

        proof_result = ProofResult(
            job_id=job.job_id,
            applicant_verified=job.verification_status.value == "verified",
            cv_data=extracted_data,
            matching_result=result,
            proof_data=None,
        )
        proof_results.append(proof_result)

    return matching_results, proof_results


@router.post("/upload-cv", response_model=CVUploadResponse, summary="Upload and process a CV (PDF)")
async def upload_cv(file: UploadFile = File(...), job_id: Optional[str] = Form(None)):
    """
    Upload a raw PDF CV for processing:
    1. Validate uploaded PDF payload
    2. Forward raw PDF bytes to LMM Agent (Person B module)
    3. Validate LMM response with Pydantic
    4. Run rules engine against all active jobs
    5. Generate matching results
    6. Return processed results
    
    Args:
        file: PDF file upload
        job_id: Optional job ID to filter results
        
    Returns:
        CVUploadResponse with extracted data and matching results
    """
    try:
        # Step 0: Validate file metadata
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise ValueError("File must be a PDF")

        # Read raw PDF payload
        pdf_content = await file.read()
        if not pdf_content:
            raise ValueError("PDF file is empty")

        # Lightweight signature check; extraction is delegated to Person B.
        if not pdf_content.startswith(b"%PDF"):
            raise ValueError("File is not a valid PDF")

        # Step 1: Forward raw PDF bytes to LMM Agent (Person B module)
        extracted_data = await lmm_agent_client.extract_cv_from_pdf(
            pdf_content=pdf_content,
            filename=file.filename,
            job_id=job_id,
        )
        
        # Step 2: Run rules engine against each job
        matching_results, proof_results = _build_results(extracted_data)
        
        # Step 4: Save and return results
        upload_id = str(uuid.uuid4())
        upload_data = {
            "upload_id": upload_id,
            "cv_source": "pdf",
            "pdf_filename": file.filename,
            "extracted_text": None,
            "extracted_data": extracted_data.model_dump(),
            "matching_results": [r.model_dump() for r in matching_results],
            "proof_results": [p.model_dump() for p in proof_results],
        }
        db.save_cv_upload(upload_data)
        
        return CVUploadResponse(
            upload_id=upload_id,
            cv_source="pdf",
            extracted_text=None,
            extracted_data=extracted_data,
            matching_results=matching_results,
            proof_results=proof_results,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")


@router.post("/upload-cv-pdf", response_model=CVUploadResponse, summary="Upload and process a CV from PDF")
async def upload_cv_pdf(file: UploadFile = File(...), job_id: Optional[str] = Form(None)):
    """
    Upload a raw PDF CV for processing:
    1. Validate uploaded PDF payload
    2. Forward raw PDF bytes to LMM Agent (Person B module)
    3. Validate LMM response with Pydantic
    4. Run rules engine against all active jobs
    5. Return processed results
    
    Args:
        file: PDF file upload
        job_id: Optional job ID to filter results
        
    Returns:
        CVUploadResponse with extracted data and matching results
    """
    # Compatibility alias: keep legacy route while using the same PDF flow as /upload-cv.
    return await upload_cv(file=file, job_id=job_id)


@router.get("/cv-upload/{upload_id}", response_model=CVUploadResponse, summary="Get CV upload result")
async def get_cv_upload(upload_id: str):
    """
    Retrieve a previously uploaded CV's processing results.
    
    Args:
        upload_id: The upload ID from the upload response
        
    Returns:
        CVUploadResponse with all processing results
    """
    try:
        upload_data = db.get_cv_upload(upload_id)
        
        return CVUploadResponse(
            upload_id=upload_data["upload_id"],
            cv_source=upload_data.get("cv_source", "pdf"),
            extracted_text=upload_data.get("extracted_text"),
            extracted_data=ExtractedCVData(**upload_data["extracted_data"]),
            matching_results=[RulesEngineResult(**r) for r in upload_data["matching_results"]],
            proof_results=[ProofResult(**p) for p in upload_data["proof_results"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving upload: {str(e)}")
