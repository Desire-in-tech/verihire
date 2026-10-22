"""Employer result projection. No Midnight service and no CV upload."""

from __future__ import annotations

import json
import unittest

from Backend.employer_results import public_employer_results
from Backend.models import Job, JobCriteria, VerificationStatus


def _job() -> Job:
    return Job(
        job_id="job-004",
        title="Python Backend Developer — Midnight Demo",
        company="Example",
        description="demo",
        criteria=JobCriteria(required_skills={"python": 2}),
        verification_status=VerificationStatus.VERIFIED,
    )


class EmployerResultTests(unittest.TestCase):
    def test_stored_flag_cannot_invent_a_verified_candidate(self) -> None:
        uploads = [
            {
                "upload_id": "upload-1",
                "extracted_text": "SECRET-CV-TEXT",
                "extracted_data": {"skills": {"python": 9}, "summary": "SECRET-SUMMARY"},
                "proof_results": [
                    {
                        "job_id": "job-004",
                        "applicant_verified": True,
                        "cv_data": {"summary": "SECRET-CV-DATA"},
                        "matching_result": {"job_id": "job-004", "matches": False, "score": 40},
                        "proof_data": {
                            "verification_status": "failed",
                            "eligible": True,
                            "proof_id": "tx-failed",
                            "message": "verification failed",
                        },
                    }
                ],
            }
        ]
        rows = public_employer_results(uploads, {"job-004": _job()})
        encoded = json.dumps(rows)
        self.assertNotIn("SECRET-CV-TEXT", encoded)
        self.assertNotIn("SECRET-SUMMARY", encoded)
        self.assertNotIn("SECRET-CV-DATA", encoded)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["applicant_verified"])
        self.assertEqual(rows[0]["proof_data"]["verification_status"], "failed")
        self.assertIsNone(rows[0]["proof_data"]["eligible"])
        self.assertEqual(rows[0]["proof_data"]["proof_id"], "tx-failed")
        self.assertEqual(rows[0]["job_title"], "Python Backend Developer — Midnight Demo")
        self.assertEqual(rows[0]["match_score"], 40)

    def test_verified_eligible_is_the_only_positive_claim(self) -> None:
        uploads = [
            {
                "upload_id": "upload-2",
                "proof_results": [
                    {
                        "job_id": "job-004",
                        "applicant_verified": False,
                        "matching_result": {"matches": True, "score": 88},
                        "proof_data": {
                            "verification_status": "verified",
                            "eligible": True,
                            "proof_id": "tx-ok",
                            "block_height": 3,
                            "message": "Eligible, verification succeeded.",
                        },
                    },
                    {
                        "job_id": "job-004",
                        "applicant_verified": True,
                        "proof_data": {
                            "verification_status": "unknown",
                            "eligible": True,
                            "proof_id": "tx-pending",
                            "message": "Do not resubmit it automatically.",
                        },
                    },
                ],
            }
        ]
        rows = public_employer_results(uploads, {"job-004": _job()})
        self.assertEqual([row["applicant_verified"] for row in rows], [True, False])
        self.assertEqual(rows[1]["proof_data"]["verification_status"], "unknown")
        self.assertIsNone(rows[1]["proof_data"]["eligible"])
        self.assertEqual(rows[1]["proof_data"]["proof_id"], "tx-pending")

    def test_empty_store_has_no_rows(self) -> None:
        self.assertEqual(public_employer_results([], {"job-004": _job()}), [])


if __name__ == "__main__":
    unittest.main()
