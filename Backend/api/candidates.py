"""
Endpoints for the candidate side of VeriHire:

  POST /api/candidates                          - register a candidate from CV text or an uploaded PDF
  POST /api/candidates/{id}/apply/{job_id}      - apply to a job (proof, no PII)
  POST /api/candidates/{id}/disclose/{job_id}   - progressively reveal more info

This is where "progressive disclosure" actually happens:

  1. POST /api/candidates stores the candidate privately and returns only
     an anonymized reference (e.g. "PX-104") - never the raw CV or contact
     info. Accepts either JSON {"cv_text": "..."} or a multipart PDF file
     upload; a PDF is run through pdfplumber to extract its text first,
     then both paths call the same AI extraction step.
  2. POST /api/candidates/{id}/apply/{job_id} runs the rules engine and
     the Midnight proof (real or mocked), and returns a verified/
     unverified checklist tied to the anonymized ref - still no name,
     email, or phone.
  3. POST /api/candidates/{id}/disclose/{job_id} is the candidate
     explicitly opting in to reveal more (their choice, not automatic) -
     moving to "full_disclosure" is what finally releases their contact
     info to that specific employer/job.
"""

import io

import pdfplumber
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from typing import Optional

from ai_client import extract_cv
from database import db
from midnight_client import generate_proof
from models import (
    ApplicationResult,
    CandidateProfile,
    DisclosureLevel,
)
from rules_engine import evaluate

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


class PDFExtractionError(Exception):
    """Raised when a PDF can't be parsed or contains no extractable text."""
    pass


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract plain text from raw PDF bytes, pages joined by double newlines."""
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        raise PDFExtractionError(f"Could not parse PDF: {e}")

    full_text = "\n\n".join(text_parts).strip()

    if not full_text:
        raise PDFExtractionError(
            "No extractable text found in PDF (it may be a scanned image with no text layer)"
        )

    return full_text


@router.post(
    "",
    response_model=CandidateProfile,
    response_model_exclude={"name", "email", "phone", "extraction", "extracted_text"},
    summary="Register a candidate from CV text or an uploaded PDF",
)
async def create_candidate(
    file: Optional[UploadFile] = File(None),
    cv_text: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
):
    """
    Registers a new candidate from either an uploaded PDF (`file`) or raw
    CV text (`cv_text`) - exactly one of the two must be provided. AI #1
    extracts structured credentials from the resulting text; the raw CV
    text itself is never returned by this endpoint (response_model_exclude
    above) - only the candidate_id + anonymized_ref are needed to continue.
    """
    if file is None and not cv_text:
        raise HTTPException(status_code=422, detail="Provide either a PDF file or cv_text")
    if file is not None and cv_text:
        raise HTTPException(status_code=422, detail="Provide either a PDF file or cv_text, not both")

    cv_source = "text"
    extracted_text = cv_text

    if file is not None:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="File must be a PDF")

        pdf_content = await file.read()
        if not pdf_content:
            raise HTTPException(status_code=422, detail="PDF file is empty")
        if not pdf_content.startswith(b"%PDF"):
            raise HTTPException(status_code=422, detail="File is not a valid PDF")

        try:
            extracted_text = extract_text_from_pdf(pdf_content)
        except PDFExtractionError as e:
            raise HTTPException(status_code=422, detail=str(e))

        cv_source = "pdf"

    extraction = extract_cv(extracted_text)

    candidate = CandidateProfile(
        candidate_id=db.new_id(),
        anonymized_ref=db.next_anonymized_ref(),
        name=name,
        email=email,
        phone=phone,
        extraction=extraction,
        cv_source=cv_source,
        extracted_text=extracted_text,
    )
    db.save_candidate(candidate)
    return candidate


@router.post("/{candidate_id}/apply/{job_id}", response_model=ApplicationResult)
def apply_to_job(candidate_id: str, job_id: str):
    try:
        candidate = db.get_candidate(candidate_id)
        job = db.get_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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
    db.save_application(candidate_id, job_id, result)
    return result


@router.post("/{candidate_id}/disclose/{job_id}", response_model=ApplicationResult)
def disclose(candidate_id: str, job_id: str, level: DisclosureLevel):
    """
    The candidate chooses to move up a disclosure stage for one specific
    application. This is an explicit, candidate-initiated action - nothing
    else in the system escalates disclosure automatically.
    """
    try:
        candidate = db.get_candidate(candidate_id)
        application = db.get_application(candidate_id, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    candidate.disclosure_level = level
    db.save_candidate(candidate)

    application.disclosure_level = level
    if level == DisclosureLevel.FULL_DISCLOSURE:
        application.contact = {
            "name": candidate.name or "",
            "email": candidate.email or "",
            "phone": candidate.phone or "",
        }
    db.save_application(candidate_id, job_id, application)
    return application
