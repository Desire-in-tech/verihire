"""Midnight outcome tests. No node, proof server, or wallet."""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

import httpx

from Backend.midnight_client import MidnightClient, applicant_verified_from_proof
from Backend.models import (
    ExtractedCVData,
    Job,
    JobCriteria,
    ProofResult,
    RulesEngineResult,
    VerificationStatus,
)


def _job(**criteria_kwargs: object) -> Job:
    criteria = dict(
        required_skills={"python": 3, "postgresql": 0},
        min_years_experience=0,
        education_level="bachelors",
        languages=[],
        certifications=["aws_certified"],
    )
    criteria.update(criteria_kwargs)
    return Job(
        job_id="job-supported",
        title="Backend Engineer",
        company="Example",
        description="Supported circuit shape",
        criteria=JobCriteria(**criteria),
        verification_status=VerificationStatus.VERIFIED,
    )


def _job_001() -> Job:
    return Job(
        job_id="job-001",
        title="Senior Python Developer",
        company="TechCorp Inc",
        description="Seed flagship job",
        criteria=JobCriteria(
            required_skills={
                "python": 5,
                "fastapi": 3,
                "postgresql": 2,
                "docker": 2,
            },
            min_years_experience=5,
            education_level="bachelors",
            languages=["English"],
            certifications=[],
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _seed_job(job_id: str) -> Job:
    path = Path(__file__).resolve().parents[1] / "data" / "seed_jobs.json"
    payload = json.loads(path.read_text())
    match = next(job for job in payload["jobs"] if job["job_id"] == job_id)
    return Job(
        job_id=match["job_id"],
        title=match["title"],
        company=match["company"],
        description=match["description"],
        criteria=JobCriteria(**match["criteria"]),
        verification_status=VerificationStatus(match["verification_status"]),
        is_active=match.get("is_active", True),
    )


def _candidate(**kwargs: object) -> ExtractedCVData:
    data = dict(
        skills={"python": 4, "postgresql": 1},
        education_level="bachelors",
        certifications=["aws_certified"],
        languages=[],
    )
    data.update(kwargs)
    return ExtractedCVData(**data)


def _result(job: Job) -> ProofResult:
    return ProofResult(
        job_id=job.job_id,
        applicant_verified=False,
        cv_data=_candidate(),
        matching_result=RulesEngineResult(
            job_id=job.job_id,
            matches=False,
            score=0,
            missing_requirements=[],
            matched_requirements=[],
            reasoning="",
        ),
    )


class RecordingClient(MidnightClient):
    def __init__(self) -> None:
        super().__init__()
        self.base_url = "http://midnight.test"
        self.calls: list[dict] = []
        self.payload: dict | Exception = {}

    async def _post_json(self, payload: dict) -> dict:
        self.calls.append(payload)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def _prove(client: MidnightClient, job: Job, candidate: ExtractedCVData | None = None) -> dict:
    return asyncio.run(
        client.prove(
            upload_id="upload-1",
            job=job,
            candidate=candidate or _candidate(),
            result=_result(job),
        )
    )


class MidnightOutcomeTests(unittest.TestCase):
    def test_verified_eligible_sets_applicant_verified(self) -> None:
        client = RecordingClient()
        client.payload = {
            "verification_status": "verified",
            "eligible": True,
            "unsupported_criteria": [],
            "proof_id": "tx-eligible",
            "block_height": 10,
            "message": "Eligible, verification succeeded.",
        }
        proof = _prove(client, _job())
        self.assertEqual(proof["verification_status"], "verified")
        self.assertIs(proof["eligible"], True)
        self.assertEqual(proof["proof_id"], "tx-eligible")
        self.assertEqual(proof["block_height"], 10)
        self.assertEqual(proof["unsupported_criteria"], [])
        self.assertTrue(applicant_verified_from_proof(proof))
        self.assertEqual(len(client.calls), 1)
        self.assertIs(client.calls[0]["has_bachelors_or_equivalent"], True)

    def test_verified_ineligible_is_not_applicant_verified(self) -> None:
        client = RecordingClient()
        client.payload = {
            "verification_status": "verified",
            "eligible": False,
            "proof_id": "tx-ineligible",
            "block_height": 11,
            "message": "Not eligible, verification succeeded.",
        }
        proof = _prove(client, _job())
        self.assertEqual(proof["verification_status"], "verified")
        self.assertIs(proof["eligible"], False)
        self.assertEqual(proof["proof_id"], "tx-ineligible")
        self.assertFalse(applicant_verified_from_proof(proof))

    def test_failed_service_result_leaves_eligible_unknown(self) -> None:
        client = RecordingClient()
        client.payload = {
            "verification_status": "failed",
            "eligible": False,
            "proof_id": "tx-missing-key",
            "block_height": 12,
            "message": "The transaction returned but the result key is not in the ledger.",
        }
        proof = _prove(client, _job())
        self.assertEqual(proof["verification_status"], "failed")
        self.assertIsNone(proof["eligible"])
        self.assertEqual(proof["proof_id"], "tx-missing-key")
        self.assertFalse(applicant_verified_from_proof(proof))

    def test_service_unavailable_is_not_positive(self) -> None:
        client = RecordingClient()
        client.payload = httpx.ConnectError("connection refused")
        proof = _prove(client, _job())
        self.assertEqual(proof["verification_status"], "unavailable")
        self.assertIsNone(proof["eligible"])
        self.assertIsNone(proof["proof_id"])
        self.assertEqual(proof["unsupported_criteria"], [])
        self.assertFalse(applicant_verified_from_proof(proof))

    def test_not_configured_makes_no_http_call(self) -> None:
        client = RecordingClient()
        client.base_url = ""
        proof = _prove(client, _job())
        self.assertEqual(proof["verification_status"], "not_configured")
        self.assertIsNone(proof["eligible"])
        self.assertIsNone(proof["proof_id"])
        self.assertEqual(proof["unsupported_criteria"], [])
        self.assertEqual(client.calls, [])
        self.assertFalse(applicant_verified_from_proof(proof))

    def test_job_001_is_refused_and_lists_every_uncovered_field(self) -> None:
        client = RecordingClient()
        proof = _prove(client, _job_001())
        self.assertIsNone(proof["verification_status"])
        self.assertIsNone(proof["eligible"])
        self.assertIsNone(proof["proof_id"])
        self.assertEqual(
            proof["unsupported_criteria"],
            [
                "skill fastapi: 3 years",
                "postgresql: 2 years required; circuit checks presence only",
                "skill docker: 2 years",
                "min_years_experience: 5",
                "language: English",
            ],
        )
        self.assertEqual(client.calls, [])
        self.assertFalse(applicant_verified_from_proof(proof))

    def test_other_unsupported_criteria_are_listed(self) -> None:
        job = _job(
            required_skills={"python": 1, "kubernetes": 2},
            education_level="masters",
            certifications=["aws solutions architect associate"],
            languages=["French"],
            min_years_experience=4,
        )
        listed = MidnightClient.unsupported_criteria(job)
        self.assertIn("skill kubernetes: 2 years", listed)
        self.assertIn("education_level: masters", listed)
        self.assertIn("certification: aws solutions architect associate", listed)
        self.assertIn("language: French", listed)
        self.assertIn("min_years_experience: 4", listed)

    def test_equivalent_experience_does_not_count_as_bachelors(self) -> None:
        client = RecordingClient()
        client.payload = {
            "verification_status": "verified",
            "eligible": False,
            "proof_id": "tx-education",
            "block_height": 4,
        }
        _prove(client, _job(), _candidate(education_level="equivalent_experience"))
        self.assertIs(client.calls[0]["has_bachelors_or_equivalent"], False)
        self.assertIs(client.calls[0]["require_bachelors"], True)

    def test_non_boolean_eligible_is_never_verified(self) -> None:
        for eligible in (1, 0, None, "true"):
            client = RecordingClient()
            client.payload = {
                "verification_status": "verified",
                "eligible": eligible,
                "proof_id": "tx-nonbool",
                "block_height": 3,
                "message": "should not be trusted",
            }
            proof = _prove(client, _job())
            self.assertNotEqual(proof["verification_status"], "verified", eligible)
            self.assertEqual(proof["verification_status"], "unavailable", eligible)
            self.assertIsNone(proof["eligible"], eligible)
            self.assertIsNone(proof["proof_id"], eligible)
            self.assertFalse(applicant_verified_from_proof(proof), eligible)

    def test_malformed_or_incomplete_response_is_never_eligible(self) -> None:
        incomplete_payloads = [
            {"verification_status": "verified", "eligible": True},
            {"verification_status": "verified", "proof_id": "tx-only"},
            {"status": "verified", "verified": True, "proof_id": "legacy"},
            {"verification_status": "verified", "eligible": "yes", "proof_id": "tx"},
            [],
        ]
        for payload in incomplete_payloads:
            client = RecordingClient()
            client.payload = payload  # type: ignore[assignment]
            proof = _prove(client, _job())
            self.assertEqual(proof["verification_status"], "unavailable", payload)
            self.assertIsNone(proof["eligible"], payload)
            self.assertIsNone(proof["proof_id"], payload)
            self.assertFalse(applicant_verified_from_proof(proof))

    def test_seed_demo_job_reaches_prove_with_circuit_thresholds(self) -> None:
        client = RecordingClient()
        client.payload = {
            "verification_status": "verified",
            "eligible": True,
            "proof_id": "tx-demo",
            "block_height": 2,
            "message": "Eligible, verification succeeded.",
        }
        job = _seed_job("job-004")
        self.assertEqual(job.title, "Python Backend Developer — Midnight Demo")
        self.assertEqual(MidnightClient.unsupported_criteria(job), [])
        proof = _prove(
            client,
            job,
            _candidate(education_level="masters", certifications=[], skills={"python": 3, "postgresql": 1}),
        )
        self.assertEqual(len(client.calls), 1)
        sent = client.calls[0]
        self.assertEqual(sent["required_python_years"], 2)
        self.assertIs(sent["require_postgresql"], True)
        self.assertIs(sent["require_bachelors"], True)
        self.assertIs(sent["require_aws_cert"], False)
        self.assertIs(sent["has_bachelors_or_equivalent"], True)
        self.assertEqual(proof["verification_status"], "verified")
        self.assertIs(proof["eligible"], True)
        self.assertTrue(applicant_verified_from_proof(proof))

        client.payload = {
            "verification_status": "verified",
            "eligible": False,
            "proof_id": "tx-demo-no",
            "block_height": 3,
        }
        ineligible = _prove(client, job)
        self.assertEqual(ineligible["verification_status"], "verified")
        self.assertIs(ineligible["eligible"], False)
        self.assertFalse(applicant_verified_from_proof(ineligible))

        client.payload = {
            "verification_status": "verified",
            "eligible": 1,
            "proof_id": "tx-demo-bad",
        }
        unknown = _prove(client, job)
        self.assertEqual(unknown["verification_status"], "unavailable")
        self.assertIsNone(unknown["eligible"])
        self.assertFalse(applicant_verified_from_proof(unknown))

    def test_seed_job_001_is_refused_before_http(self) -> None:
        client = RecordingClient()
        proof = _prove(client, _seed_job("job-001"))
        self.assertEqual(client.calls, [])
        self.assertIsNone(proof["verification_status"])
        self.assertIsNone(proof["eligible"])
        self.assertIsNone(proof["proof_id"])
        self.assertEqual(
            proof["unsupported_criteria"],
            [
                "skill fastapi: 3 years",
                "postgresql: 2 years required; circuit checks presence only",
                "skill docker: 2 years",
                "min_years_experience: 5",
                "language: English",
            ],
        )
        self.assertFalse(applicant_verified_from_proof(proof))

    def test_http_error_cannot_carry_a_positive_eligibility(self) -> None:
        request = httpx.Request("POST", "http://midnight.test/prove")
        response = httpx.Response(
            502,
            json={
                "verification_status": "verified",
                "eligible": True,
                "proof_id": "tx-should-not-count",
            },
            request=request,
        )
        client = RecordingClient()
        client.payload = httpx.HTTPStatusError("bad gateway", request=request, response=response)
        proof = _prove(client, _job())
        self.assertEqual(proof["verification_status"], "failed")
        self.assertIsNone(proof["eligible"])
        self.assertFalse(applicant_verified_from_proof(proof))


if __name__ == "__main__":
    unittest.main()
