"""
What this file does
--------------------
The backend's only connection to the AI extraction service - every other
file in this codebase that needs "AI-extracted data" calls one of the two
functions here instead of making HTTP calls itself. That keeps the
HTTP/JSON plumbing (and its error handling) in one place.

Both functions call the AI service over plain HTTP using httpx, send JSON
matching the *Request models, and validate the response JSON against the
backend's own copies of ExtractionResult / JobRequirements (see the note in
models.py about why these are duplicated rather than imported).

If the AI service is down or returns something unexpected, we raise a
clear HTTPException rather than letting a confusing low-level error bubble
up - this is exactly the kind of thing the pitch doc's "Pydantic checks
data at the door" argument is about, just applied at the boundary between
our two services instead of between the AI and a single app.
"""

import httpx
from fastapi import HTTPException

from .config import settings
from .models import ExtractionResult, JobRequirements

_TIMEOUT = httpx.Timeout(30.0)


def extract_cv(cv_text: str) -> ExtractionResult:
    try:
        response = httpx.post(
            f"{settings.ai_service_url}/extract",
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
    try:
        response = httpx.post(
            f"{settings.ai_service_url}/parse-job",
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
