"""
AI Service Client - CV Extraction

Pipeline:

    PDF
      ↓
    pdf_extractor.py
      ↓
    plain CV text
      ↓
    POST /extract
      ↓
    structured CV data
"""

import httpx
from typing import Any

from Backend.models import ExtractedCVData
from Backend.config import get_settings


class LMMAgentClient:
    """Client for the VeriHire AI extraction service."""

    def __init__(self):
        self.settings = get_settings()

        self.base_url = (
            getattr(self.settings, "AI_SERVICE_URL", None)
            or getattr(self.settings, "LMM_AGENT_URL", None)
            or "http://localhost:8001"
        ).rstrip("/")

        self.extract_endpoint = f"{self.base_url}/extract"

        self.timeout = float(
            getattr(self.settings, "AI_SERVICE_TIMEOUT", 60.0)
        )

    async def extract_cv(self, cv_text: str) -> ExtractedCVData:
        """
        Send plain CV text to the AI service and return validated
        structured candidate data.
        """

        if not cv_text or not cv_text.strip():
            raise ValueError("CV text cannot be empty")

        payload = {
            "cv_text": cv_text.strip()
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.extract_endpoint,
                    json=payload,
                )

                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                "AI service returned HTTP "
                f"{exc.response.status_code}: {exc.response.text}"
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                "Could not connect to AI service at "
                f"{self.extract_endpoint}: {exc}"
            ) from exc

        try:
            response_data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ValueError(
                "AI service returned invalid JSON"
            ) from exc

        return self._parse_response(response_data)

    def _parse_response(
        self,
        response_data: dict[str, Any],
    ) -> ExtractedCVData:
        """
        Convert the AI service response into the Backend's
        ExtractedCVData contract.

        Expected AI response:

            {
                "skills": {
                    "python": 4,
                    "fastapi": 2
                },
                "certifications": [],
                "education_level": "bachelors",
                "raw_summary": "..."
            }
        """

        try:
            raw_skills = response_data.get("skills", {})

            if not isinstance(raw_skills, dict):
                raise ValueError("skills must be an object")

            skills: dict[str, int] = {}

            for skill, years in raw_skills.items():
                if not isinstance(skill, str):
                    continue

                try:
                    years_int = int(years)
                except (TypeError, ValueError):
                    years_int = 0

                skills[skill.strip().lower()] = max(0, years_int)

            certifications = response_data.get(
                "certifications",
                []
            )

            if not isinstance(certifications, list):
                raise ValueError("certifications must be a list")

            normalized_certifications = [
                cert.strip().lower()
                for cert in certifications
                if isinstance(cert, str) and cert.strip()
            ]

            languages = response_data.get("languages", [])
            if not isinstance(languages, list):
                raise ValueError("languages must be a list")
            normalized_languages = [
                language.strip().lower()
                for language in languages
                if isinstance(language, str) and language.strip()
            ]

            education_level = response_data.get(
                "education_level"
            )

            if education_level is not None:
                education_level = str(
                    education_level
                ).strip().lower()

            summary = response_data.get("raw_summary")

            if summary is not None:
                summary = str(summary).strip()

            return ExtractedCVData(
                skills=skills,
                languages=normalized_languages,
                certifications=normalized_certifications,
                education_level=education_level,
                summary=summary,
            )

        except ValueError as exc:
            raise ValueError(
                f"AI service returned invalid CV data: {exc}"
            ) from exc

        except Exception as exc:
            raise ValueError(
                f"Failed to parse AI service response: {exc}"
            ) from exc
