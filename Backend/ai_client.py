"""
The backend's only connection to the AI extraction service - every other
file in this codebase that needs "AI-extracted data" calls one of the two
functions here instead of making HTTP calls itself.

Both functions call the AI service over plain HTTP using httpx, send JSON
matching its *Request models, and validate the response JSON against this
backend's own copies of ExtractionResult / JobRequirements (see the note in
models.py about why these are duplicated rather than imported - the two
services are meant to be independently deployable).

If the AI service is down or returns something unexpected, we raise a
clear HTTPException rather than letting a confusing low-level error bubble
up.
"""

import httpx
from fastapi import HTTPException

from config import get_settings
from models import ExtractionResult, JobRequirements

_TIMEOUT = httpx.Timeout(30.0)


def extract_cv(cv_text: str) -> ExtractionResult:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.AI_SERVICE_URL}/extract",
            json={"cv_text": cv_text},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI extraction service unreachable: {exc}") from exc

    try:
        return ExtractionResult.model_validate(response.json())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service returned an unexpected shape: {exc}") from exc


def extract_job_requirements(description: str) -> JobRequirements:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.AI_SERVICE_URL}/parse-job",
            json={"description": description},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI extraction service unreachable: {exc}") from exc

    try:
        return JobRequirements.model_validate(response.json())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service returned an unexpected shape: {exc}") from exc
