"""Small HTTP client for the Midnight verification service.

The FastAPI service deliberately knows only this HTTP contract. Midnight.js,
wallet handling, proof generation, and transaction submission stay in the
Node service where the official Midnight SDK belongs.
"""

from __future__ import annotations

from typing import Any

import httpx

from Backend.config import get_settings
from Backend.models import ExtractedCVData, Job, ProofResult


class MidnightClient:
    """Call the real Midnight service when it is configured."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (self.settings.MIDNIGHT_SERVICE_URL or "").rstrip("/")
        self.timeout = self.settings.MIDNIGHT_SERVICE_TIMEOUT

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    @staticmethod
    def supports_job(job: Job) -> bool:
        """The MVP circuit is intentionally fixed-shape and only maps job-001."""
        return job.job_id == "job-001"

    @staticmethod
    def _circuit_inputs(
        candidate: ExtractedCVData,
        job: Job,
    ) -> dict[str, Any]:
        required_skills = {key.lower(): value for key, value in job.criteria.required_skills.items()}
        candidate_skills = {key.lower(): value for key, value in candidate.skills.items()}
        certifications = {value.lower() for value in candidate.certifications}
        education = (candidate.education_level or "").lower()

        return {
            "python_years": max(0, candidate_skills.get("python", 0)),
            "has_postgresql": "postgresql" in candidate_skills,
            "has_aws_cert": "aws_certified" in certifications,
            "has_bachelors_or_equivalent": education in {
                "bachelors",
                "masters",
                "phd",
                "equivalent_experience",
            },
            "required_python_years": max(0, required_skills.get("python", 0)),
            "require_postgresql": "postgresql" in required_skills,
            "require_aws_cert": "aws_certified" in job.criteria.certifications,
            "require_bachelors": job.criteria.education_level not in {None, "", "none"},
        }

    async def prove(
        self,
        *,
        upload_id: str,
        job: Job,
        candidate: ExtractedCVData,
        result: ProofResult,
    ) -> dict[str, Any]:
        if not self.configured:
            return {
                "status": "not_configured",
                "mode": "local_fallback",
                "message": "Midnight service is not configured; no proof was generated.",
            }

        if not self.supports_job(job):
            return {
                "status": "unsupported_job",
                "mode": "local_fallback",
                "message": "This job is evaluated by the rules engine; the fixed MVP circuit does not cover it.",
            }

        import hashlib

        result_key = hashlib.sha256(f"{upload_id}:{job.job_id}".encode()).hexdigest()
        payload = {
            "result_key": result_key,
            **self._circuit_inputs(candidate, job),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/prove", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Midnight service returned HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not connect to Midnight service at {self.base_url}: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("Midnight service returned invalid JSON") from exc

        if data.get("status") != "verified" or not data.get("proof_id"):
            raise RuntimeError("Midnight service did not return a verified proof")

        return data