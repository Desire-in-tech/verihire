"""
This is what api/candidates.py actually calls to get a "Midnight proof" -
it is the single decision point for "do we call the real Midnight
service, or fall back to the offline mock":

  - If MIDNIGHT_SERVICE_URL is unset (the default), we go straight to the
    offline mock in midnight_mock.py. No network call is attempted.
  - If it IS set, we POST the candidate's private extraction data plus the
    job's public requirements to that service's `/prove` endpoint (see
    midnight_service/src/server.ts - a small Node/TypeScript HTTP wrapper
    around the real @midnight-ntwrk SDK calls, since Midnight's tooling is
    JS/TypeScript-based, not Python). If that call fails for any reason
    (service down, still syncing, mid-setup), we log a warning and fall
    back to the offline mock rather than breaking the whole request.

IMPORTANT design point: we deliberately send the RAW private extraction
values (skills/certs/education) here, not just the already-computed
MatchResult booleans. If we only ever sent Python's finished verdict for
Midnight to echo back, "the proof" would be theater - Midnight has to do
its own private computation from the private inputs for the proof to mean
anything. The `_map_to_circuit_inputs` function below is the (currently
narrow) translation from our generic schema to the contract's fixed-shape
circuit inputs - see contract/verihire.compact's own docstring for why
that shape is fixed rather than fully generic.

IMPORTANT status note: midnight_service/ contains real Compact source and
a real Node/TypeScript service scaffold, but it has NOT been compiled,
deployed, or run end-to-end in this environment (that requires the
Compact compiler, a local proof-server Docker container, Midnight
node+indexer RPC access, and a funded testnet wallet - see
midnight_service/README.md). Until MIDNIGHT_SERVICE_URL is set and points
at a real running instance, every proof in this app comes from the
offline mock above, and that's expected, not a bug.
"""

import hashlib
import sys

import httpx

from config import get_settings
from midnight_mock import generate_proof as generate_mock_proof
from models import ExtractionResult, JobRequirements, MatchResult, ProofResult

_TIMEOUT = httpx.Timeout(15.0)


def _result_key(candidate_ref: str, job_id: str) -> str:
    """The public, opaque identifier for a (candidate, job) proof - never the candidate's real identity."""
    return hashlib.sha256(f"{candidate_ref}:{job_id}".encode("utf-8")).hexdigest()


def _map_to_circuit_inputs(extraction: ExtractionResult, requirements: JobRequirements) -> dict:
    """
    Translates our generic schema into the fixed four-criteria shape that
    contract/verihire.compact's proveEligibility circuit actually accepts
    (Python years / PostgreSQL / AWS cert / Bachelor's-or-equivalent).

    This only faithfully represents jobs whose requirements are drawn from
    those four criteria. A job that asks for Kubernetes or a Master's
    degree instead still produces a result (missing criteria just default
    to "not required"/"not held"), but that result would NOT reflect the
    job's actual full requirement set - a known MVP limitation, not a bug.
    """
    education_ok_values = {"bachelors", "masters", "phd", "equivalent_experience"}
    return {
        "python_years": extraction.skills.get("python", 0),
        "has_postgresql": "postgresql" in extraction.skills,
        "has_aws_cert": "aws_certified" in extraction.certifications,
        "has_bachelors_or_equivalent": extraction.education_level.value in education_ok_values,
        "required_python_years": requirements.required_skills.get("python", 0),
        "require_postgresql": "postgresql" in requirements.required_skills,
        "require_aws_cert": "aws_certified" in requirements.required_certifications,
        "require_bachelors": requirements.min_education_level is not None,
    }


def generate_proof(match: MatchResult, extraction: ExtractionResult, requirements: JobRequirements) -> ProofResult:
    settings = get_settings()
    if not settings.has_midnight_service:
        return generate_mock_proof(match)

    try:
        payload = {
            "result_key": _result_key(match.candidate_ref, match.job_id),
            **_map_to_circuit_inputs(extraction, requirements),
        }
        response = httpx.post(f"{settings.MIDNIGHT_SERVICE_URL}/prove", json=payload, timeout=_TIMEOUT)
        response.raise_for_status()
        return ProofResult.model_validate(response.json())
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure falls back
        print(f"[midnight_client] real Midnight service unreachable ({exc}); using offline mock proof", file=sys.stderr)
        return generate_mock_proof(match)
