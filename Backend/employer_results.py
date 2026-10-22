"""Employer-facing proof rows.

Employers see the Midnight claim and the match score. Raw CV text and
extracted credentials stay on the stored upload.
"""

from __future__ import annotations

from typing import Any

from Backend.midnight_client import applicant_verified_from_proof
from Backend.models import Job

_STATUSES = {None, "verified", "failed", "unavailable", "not_configured", "unknown"}


def _public_proof(proof_data: dict[str, Any]) -> dict[str, Any]:
    status = proof_data.get("verification_status")
    if status not in _STATUSES:
        status = "unavailable"

    eligible = proof_data.get("eligible")
    if status != "verified" or not (eligible is True or eligible is False):
        eligible = None

    proof_id = proof_data.get("proof_id")
    block_height = proof_data.get("block_height")
    unsupported = proof_data.get("unsupported_criteria")
    if not isinstance(unsupported, list):
        unsupported = []

    public = {
        "verification_status": status,
        "eligible": eligible,
        "unsupported_criteria": [item for item in unsupported if isinstance(item, str)],
        "proof_id": proof_id if isinstance(proof_id, str) and proof_id else None,
        "block_height": block_height if isinstance(block_height, int) else None,
        "message": str(proof_data.get("message") or ""),
    }
    if status == "unknown" and not public["proof_id"]:
        public["verification_status"] = "unavailable"
        public["eligible"] = None
    return public


def public_employer_results(
    uploads: list[dict[str, Any]],
    jobs_by_id: dict[str, Job],
) -> list[dict[str, Any]]:
    """Project stored uploads into claims an employer can display."""
    rows: list[dict[str, Any]] = []
    for upload in uploads:
        upload_id = upload.get("upload_id")
        if not isinstance(upload_id, str) or not upload_id.strip():
            continue
        proofs = upload.get("proof_results")
        if not isinstance(proofs, list):
            continue
        for proof in proofs:
            if not isinstance(proof, dict):
                continue
            job_id = proof.get("job_id")
            if not isinstance(job_id, str) or not job_id.strip():
                continue
            raw_proof = proof.get("proof_data")
            public_proof = _public_proof(raw_proof if isinstance(raw_proof, dict) else {})
            matching = proof.get("matching_result")
            matching = matching if isinstance(matching, dict) else {}
            score = matching.get("score")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                score = None
            matches = matching.get("matches")
            job = jobs_by_id.get(job_id)
            rows.append(
                {
                    "upload_id": upload_id,
                    "job_id": job_id,
                    "job_title": job.title if job else job_id,
                    "company": job.company if job else "",
                    "match_score": score,
                    "matches": matches if isinstance(matches, bool) else None,
                    "applicant_verified": applicant_verified_from_proof(public_proof),
                    "proof_data": public_proof,
                }
            )
    return rows
