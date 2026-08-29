"""
What this file does
--------------------
The OFFLINE fallback stand-in for Midnight proof generation/verification -
used automatically whenever MIDNIGHT_SERVICE_URL isn't set, or the real
Midnight service (midnight_service/ at the repo root) can't be reached.
See midnight_client.py for the logic that decides which path to use.

This fakes the shape of a real Midnight response: a random proof id, a
hash of the claim text (stands in for a real cryptographic commitment),
and a `verified` flag that mirrors the rules engine's own verdict. It does
NOT talk to any blockchain and produces no real zero-knowledge proof - it
exists purely so the rest of the app (and a live demo) keeps working
before/without the real Midnight toolchain being provisioned.
"""

import hashlib
import uuid

from .models import MatchResult, ProofResult


def generate_proof(match: MatchResult) -> ProofResult:
    claim = (
        f"candidate {match.candidate_ref} scores {match.tier.value} "
        f"({match.score:.0%}) against requirements for {match.job_id}"
    )
    claim_hash = hashlib.sha256(claim.encode("utf-8")).hexdigest()

    return ProofResult(
        proof_id=str(uuid.uuid4()),
        verified=match.overall_match,
        claim=claim,
        claim_hash=claim_hash,
    )
