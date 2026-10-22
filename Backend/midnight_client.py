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

_CONNECTIVITY_TIMEOUT_SECONDS = 3.0
_UINT16_MAX = 65535
_BACHELORS_OR_HIGHER = {"bachelors", "masters", "phd"}
_SUPPORTED_EDUCATION = {"", "none", "bachelors"}


def empty_proof(
    *,
    verification_status: str | None,
    eligible: bool | None,
    unsupported_criteria: list[str] | None = None,
    proof_id: str | None = None,
    block_height: int | None = None,
    message: str = "",
) -> dict[str, Any]:
    """One shape for every Midnight outcome. `eligible` is never implied by status."""
    return {
        "verification_status": verification_status,
        "eligible": eligible,
        "unsupported_criteria": list(unsupported_criteria or []),
        "proof_id": proof_id,
        "block_height": block_height,
        "message": message,
    }


def applicant_verified_from_proof(proof_data: dict[str, Any] | None) -> bool:
    """True only for a finalized proof whose ledger Boolean is true."""
    if not proof_data:
        return False
    return (
        proof_data.get("verification_status") == "verified"
        and proof_data.get("eligible") is True
    )


class MidnightClient:
    """Call the real Midnight service when it is configured."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (self.settings.MIDNIGHT_SERVICE_URL or "").rstrip("/")
        self.timeout = self.settings.MIDNIGHT_SERVICE_TIMEOUT

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    async def service_health(self) -> dict[str, Any]:
        """GET the configured Midnight service /health route.

        This check does not call /prove and does not submit a transaction.
        Failures return a status payload instead of raising.
        """
        if not self.configured:
            return {
                "midnight_configured": False,
                "midnight_reachable": False,
                "midnight_status": "not_configured",
            }
        try:
            async with httpx.AsyncClient(timeout=_CONNECTIVITY_TIMEOUT_SECONDS) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return {
                "midnight_configured": True,
                "midnight_reachable": False,
                "midnight_status": "unreachable",
            }
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            return {
                "midnight_configured": True,
                "midnight_reachable": True,
                "midnight_status": "unhealthy",
            }
        result: dict[str, Any] = {
            "midnight_configured": True,
            "midnight_reachable": True,
            "midnight_status": "ok",
        }
        for key in ("contract_configured", "compiled_contract_configured", "wallet_configured"):
            value = payload.get(key)
            if isinstance(value, bool):
                result[key] = value
        network = payload.get("network")
        if isinstance(network, str) and network.isidentifier() and len(network) <= 32:
            result["network"] = network
        return result

    @staticmethod
    def unsupported_criteria(job: Job) -> list[str]:
        """Criteria proveEligibility cannot enforce.

        The circuit checks Python years, PostgreSQL presence, an AWS
        certification flag, and whether a bachelor's-or-higher degree is
        held. `equivalent_experience` does not satisfy a bachelor's
        requirement, matching RulesEngine._education_matches.
        """
        unsupported: list[str] = []
        skills = {
            key.strip().lower(): max(0, int(years))
            for key, years in job.criteria.required_skills.items()
            if isinstance(key, str)
        }

        for name, years in skills.items():
            if name == "python":
                if years > _UINT16_MAX:
                    unsupported.append(f"python: {years} years exceeds Uint16")
                continue
            if name == "postgresql" and years == 0:
                continue
            if name == "postgresql":
                unsupported.append(
                    f"postgresql: {years} years required; circuit checks presence only"
                )
                continue
            unsupported.append(f"skill {name}: {years} years")

        if job.criteria.min_years_experience:
            unsupported.append(
                f"min_years_experience: {job.criteria.min_years_experience}"
            )

        education = (job.criteria.education_level or "").strip().lower()
        if education not in _SUPPORTED_EDUCATION:
            unsupported.append(f"education_level: {education or 'none'}")

        for language in job.criteria.languages:
            if isinstance(language, str) and language.strip():
                unsupported.append(f"language: {language}")

        for cert in job.criteria.certifications:
            if isinstance(cert, str) and cert.strip().lower() != "aws_certified":
                unsupported.append(f"certification: {cert}")

        return unsupported

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
            "has_bachelors_or_equivalent": education in _BACHELORS_OR_HIGHER,
            "required_python_years": max(0, required_skills.get("python", 0)),
            "require_postgresql": "postgresql" in required_skills,
            "require_aws_cert": any(
                cert.strip().lower() == "aws_certified" for cert in job.criteria.certifications
            ),
            "require_bachelors": (job.criteria.education_level or "").strip().lower() == "bachelors",
        }

    async def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/prove", json=payload)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Midnight service returned invalid JSON")
        return data

    def _normalize_success(self, data: dict[str, Any]) -> dict[str, Any]:
        status = data.get("verification_status")
        eligible = data.get("eligible")
        proof_id = data.get("proof_id")
        block_height = data.get("block_height")
        message = data.get("message") or ""

        if status == "verified" and (eligible is True or eligible is False) and proof_id:
            return empty_proof(
                verification_status="verified",
                eligible=eligible,
                proof_id=proof_id,
                block_height=block_height if isinstance(block_height, int) else None,
                message=str(message),
            )

        if status == "failed":
            return empty_proof(
                verification_status="failed",
                eligible=None,
                proof_id=proof_id if isinstance(proof_id, str) and proof_id else None,
                block_height=block_height if isinstance(block_height, int) else None,
                message=str(message or "Midnight verification failed."),
            )

        return empty_proof(
            verification_status="unavailable",
            eligible=None,
            message="Midnight service returned an unreadable proof result",
        )

    async def prove(
        self,
        *,
        upload_id: str,
        job: Job,
        candidate: ExtractedCVData,
        result: ProofResult,
    ) -> dict[str, Any]:
        del result
        if not self.configured:
            return empty_proof(
                verification_status="not_configured",
                eligible=None,
                message="Midnight service is not configured; no proof was generated.",
            )

        unsupported = self.unsupported_criteria(job)
        if unsupported:
            return empty_proof(
                verification_status=None,
                eligible=None,
                unsupported_criteria=unsupported,
                message="No Midnight transaction was submitted.",
            )

        import hashlib

        result_key = hashlib.sha256(f"{upload_id}:{job.job_id}".encode()).hexdigest()
        payload = {
            "result_key": result_key,
            **self._circuit_inputs(candidate, job),
        }

        try:
            data = await self._post_json(payload)
        except httpx.HTTPStatusError as exc:
            body: dict[str, Any] = {}
            try:
                parsed = exc.response.json()
                if isinstance(parsed, dict):
                    body = parsed
            except ValueError:
                body = {}
            status = body.get("verification_status")
            if status not in {"failed", "unavailable"}:
                status = "failed"
            proof_id = body.get("proof_id")
            block_height = body.get("block_height")
            return empty_proof(
                verification_status=status,
                eligible=None,
                proof_id=proof_id if isinstance(proof_id, str) and proof_id else None,
                block_height=block_height if isinstance(block_height, int) else None,
                message=str(body.get("message") or body.get("detail") or exc.response.text),
            )
        except httpx.RequestError as exc:
            return empty_proof(
                verification_status="unavailable",
                eligible=None,
                message=f"Could not connect to Midnight service at {self.base_url}: {exc}",
            )
        except ValueError:
            return empty_proof(
                verification_status="unavailable",
                eligible=None,
                message="Midnight service returned invalid JSON",
            )

        if not isinstance(data, dict):
            return empty_proof(
                verification_status="unavailable",
                eligible=None,
                message="Midnight service returned invalid JSON",
            )

        return self._normalize_success(data)
