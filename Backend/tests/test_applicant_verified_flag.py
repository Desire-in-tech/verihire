"""Flag set by cv_processing.apply_proof_to_result.

FastAPI and pypdf are not installed. Process-local stubs exist only so the
real cv_processing module can be imported. The test calls that module's
helper. It does not run the upload route, PDF parsing, the AI client, or
Midnight HTTP.
"""

from __future__ import annotations

import sys
import types
import unittest


def _install_import_stubs() -> None:
    if "fastapi" not in sys.modules:
        fastapi = types.ModuleType("fastapi")

        class APIRouter:
            def __init__(self, *args, **kwargs) -> None:
                del args, kwargs

            def _decorate(self, *args, **kwargs):
                del args, kwargs

                def decorator(fn):
                    return fn

                return decorator

            post = _decorate
            get = _decorate

        fastapi.APIRouter = APIRouter
        fastapi.HTTPException = type("HTTPException", (Exception,), {})
        fastapi.UploadFile = type("UploadFile", (), {})
        fastapi.File = lambda *args, **kwargs: None
        fastapi.Form = lambda *args, **kwargs: None
        sys.modules["fastapi"] = fastapi

    if "pypdf" not in sys.modules:
        pypdf = types.ModuleType("pypdf")
        pypdf.PdfReader = type("PdfReader", (), {})
        sys.modules["pypdf"] = pypdf


_install_import_stubs()

from Backend.api import cv_processing
from Backend.models import ExtractedCVData, ProofResult, RulesEngineResult

print("helper module __file__:", cv_processing.__file__, flush=True)


def _proof_result() -> ProofResult:
    return ProofResult(
        job_id="job-supported",
        applicant_verified=True,
        cv_data=ExtractedCVData(),
        matching_result=RulesEngineResult(
            job_id="job-supported",
            matches=False,
            score=0,
            missing_requirements=[],
            matched_requirements=[],
            reasoning="",
        ),
    )


class ApplicantVerifiedFlagTests(unittest.TestCase):
    def _flag(self, proof_data: dict) -> bool:
        result = _proof_result()
        flagged = cv_processing.apply_proof_to_result(result, proof_data)
        self.assertIs(flagged, result.applicant_verified)
        self.assertIs(result.proof_data, proof_data)
        return result.applicant_verified

    def test_verified_true_is_the_only_positive_flag(self) -> None:
        self.assertIs(
            self._flag({"verification_status": "verified", "eligible": True}),
            True,
        )
        self.assertIs(
            self._flag({"verification_status": "verified", "eligible": False}),
            False,
        )

    def test_verified_non_boolean_eligible_is_not_verified(self) -> None:
        for eligible in (None, 1, 0, "true"):
            self.assertIs(
                self._flag({"verification_status": "verified", "eligible": eligible}),
                False,
                eligible,
            )

    def test_non_verified_statuses_are_never_flagged(self) -> None:
        for status in ("failed", "unavailable", "not_configured", None):
            for eligible in (True, False, None):
                self.assertIs(
                    self._flag({"verification_status": status, "eligible": eligible}),
                    False,
                    (status, eligible),
                )


if __name__ == "__main__":
    unittest.main()
