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

import os
from typing import Any

import httpx

from Backend.models import ExtractedCVData


class LMMAgentClient:
    """Client for the VeriHire AI extraction service."""

    def _endpoint(self) -> tuple[str, float, str]:
        base_url = os.environ.get("AI_SERVICE_URL", "http://localhost:8001").rstrip("/")
        timeout = float(os.environ.get("AI_SERVICE_TIMEOUT", "60"))
        token = os.environ.get("AI_SERVICE_TOKEN", "").strip()
        return f"{base_url}/extract", timeout, token

    async def extract_cv(self, cv_text: str) -> ExtractedCVData:
        """
        Send plain CV text to the AI service and return validated
        structured candidate data.
        """

        if not cv_text or not cv_text.strip():
            raise ValueError("CV text cannot be empty")

        endpoint, timeout, token = self._endpoint()
        if not token:
            raise RuntimeError("CV extraction is unavailable.")

        payload = {
            "cv_text": cv_text.strip()
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )

                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            raise RuntimeError("CV extraction is unavailable.") from exc

        except httpx.RequestError as exc:
            raise RuntimeError("CV extraction is unavailable.") from exc

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
