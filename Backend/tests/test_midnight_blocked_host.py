"""The API must not send applicant data to undocumented public provers."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from Backend.midnight_client import MidnightClient
from Backend.models import ExtractedCVData, Job, JobCriteria, ProofResult, RulesEngineResult, VerificationStatus


def _job() -> Job:
    return Job(
        job_id="job-supported",
        title="Backend Engineer",
        company="Example",
        description="Supported circuit shape",
        criteria=JobCriteria(
            required_skills={"python": 3, "postgresql": 0},
            min_years_experience=0,
            education_level="bachelors",
            languages=[],
            certifications=["aws_certified"],
        ),
        verification_status=VerificationStatus.VERIFIED,
    )


def _result() -> ProofResult:
    return ProofResult(
        job_id="job-supported",
        applicant_verified=False,
        cv_data=ExtractedCVData(skills={"python": 4, "postgresql": 1}, education_level="bachelors"),
        matching_result=RulesEngineResult(
            job_id="job-supported",
            matches=True,
            score=100,
            missing_requirements=[],
            matched_requirements=["python"],
            reasoning="",
        ),
    )


class BlockedHostTests(unittest.TestCase):
    def _prove(self, url: str) -> dict:
        client = MidnightClient()
        client.base_url = url
        candidate = ExtractedCVData(skills={"python": 4, "postgresql": 1}, education_level="bachelors")
        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=AssertionError("HTTP was attempted")):
            return asyncio.run(
                client.prove(
                    upload_id="upload-1",
                    job=_job(),
                    candidate=candidate,
                    result=_result(),
                )
            )

    def test_undocumented_proof_hosts_are_not_called(self) -> None:
        for url in (
            "https://proof-server.preprod.midnight.network",
            "https://lace-proof-pub.preprod.midnight.network",
            "https://lace-proof-pub.preview.midnight.network",
            "https://lace-proof-pub.mainnet.midnight.network",
        ):
            proof = self._prove(url)
            self.assertEqual(proof["verification_status"], "unavailable", url)
            self.assertIsNone(proof["proof_id"], url)
            self.assertIsNone(proof["eligible"], url)
            self.assertNotIn("transaction", proof["message"].lower(), url)

    def test_blocked_health_does_not_call_the_host(self) -> None:
        client = MidnightClient()
        client.base_url = "https://proof-server.preprod.midnight.network"
        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=AssertionError("HTTP was attempted")):
            health = asyncio.run(client.service_health())
        self.assertEqual(health["midnight_status"], "blocked_host")
        self.assertIs(health["midnight_reachable"], False)

    def test_empty_url_stays_not_configured(self) -> None:
        proof = self._prove("")
        self.assertEqual(proof["verification_status"], "not_configured")
        self.assertIsNone(proof["proof_id"])
        self.assertIsNone(proof["eligible"])


if __name__ == "__main__":
    unittest.main()
