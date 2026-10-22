"""Employer scoping, upload minimization, and AI auth. No Midnight network."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.pop("ENABLE_API_DOCS", None)
if "*" in os.environ.get("CORS_ORIGINS", ""):
    os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient

from Backend.api import cv_processing
from Backend.database import db
from Backend.main import app, parse_cors_origins
from Backend.models import ExtractedCVData
from Backend.store import Store

_PASSWORD = "correct-horse-1"
_SECRET = "SECRET-CV-TEXT"


def _criteria() -> dict:
    return {
        "required_skills": {"python": 1},
        "min_years_experience": 0,
        "education_level": "bachelors",
        "languages": [],
        "certifications": [],
    }


class AccessControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = {
            key: os.environ.get(key)
            for key in (
                "EMPLOYER_BOOTSTRAP_EMAIL",
                "EMPLOYER_BOOTSTRAP_PASSWORD",
                "DATABASE_URL",
                "VERIHIRE_DB_PATH",
                "AI_SERVICE_TOKEN",
                "ANTHROPIC_API_KEY",
            )
        }
        for key in self.saved:
            os.environ.pop(key, None)
        self.addCleanup(self._restore_env)
        self.db_path = str(Path(self.tmp.name) / "verihire.sqlite")
        db.use_sqlite_for_tests(self.db_path)
        cv_processing.midnight_client.base_url = ""
        self.client = TestClient(app)

        async def fake_extract(cv_text: str) -> ExtractedCVData:
            del cv_text
            return ExtractedCVData(skills={"python": 2}, education_level="bachelors")

        def fake_pdf(pdf_content: bytes) -> str:
            del pdf_content
            return _SECRET + "\nPython developer"

        cv_processing.lmm_agent_client.extract_cv = fake_extract
        cv_processing.extract_text_from_pdf = fake_pdf

    def _restore_env(self) -> None:
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _signup(self, email: str, name: str) -> dict:
        response = self.client.post(
            "/api/auth/signup",
            json={"email": email, "password": _PASSWORD, "display_name": name},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertNotIn("password", body["employer"])
        self.assertNotIn(_PASSWORD, response.text)
        return body

    def _job(self, employer_id: str, job_id: str) -> None:
        db.store.insert_job(
            {
                "job_id": job_id,
                "employer_id": employer_id,
                "title": "Backend Engineer",
                "company": "Example Co",
                "description": "Private description",
                "criteria": _criteria(),
                "verification_status": "verified",
                "is_active": True,
            }
        )

    def _upload(self, job_id: str, filename: str = "cv.pdf", content: bytes = b"%PDF-1.4\n") -> dict:
        response = self.client.post(
            "/api/upload-cv",
            data={"job_id": job_id},
            files={"file": (filename, content, "application/pdf")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_employers_cannot_read_each_other(self) -> None:
        first = self._signup("a@example.com", "Employer A")
        second = self._signup("b@example.com", "Employer B")
        self._job(first["employer"]["id"], "job-a")
        self._job(second["employer"]["id"], "job-b")
        uploaded = self._upload("job-a")
        self.assertNotIn(_SECRET, str(uploaded))
        self.assertNotIn("extracted_text", uploaded)
        self.assertNotIn("extracted_data", uploaded)
        self.assertNotIn("cv_data", str(uploaded))
        self.assertEqual(uploaded["proof_results"][0]["proof_data"]["verification_status"], "not_configured")
        self.assertIsNone(uploaded["proof_results"][0]["proof_data"]["proof_id"])
        self.assertIs(uploaded["proof_results"][0]["applicant_verified"], False)

        stored = Store(sqlite_path=self.db_path).get_upload(uploaded["upload_id"])
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertIn(_SECRET, stored["extracted_text"])
        self.assertEqual(stored["employer_id"], first["employer"]["id"])

        header_a = {"Authorization": f"Bearer {first['token']}"}
        header_b = {"Authorization": f"Bearer {second['token']}"}
        own = self.client.get("/api/employer/results", headers=header_a)
        other = self.client.get("/api/employer/results", headers=header_b)
        self.assertEqual(own.status_code, 200)
        self.assertEqual(len(own.json()["results"]), 1)
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.json()["results"], [])
        self.assertNotIn(_SECRET, own.text)

        spoofed = self.client.get(
            f"/api/employer/results?employer_id={second['employer']['id']}",
            headers=header_a,
        )
        self.assertEqual(len(spoofed.json()["results"]), 1)
        self.assertEqual(spoofed.json()["results"][0]["job_id"], "job-a")

        hidden = self.client.get(f"/api/cv-upload/{uploaded['upload_id']}", headers=header_b)
        self.assertEqual(hidden.status_code, 404)
        self.assertNotIn(_SECRET, hidden.text)
        visible = self.client.get(f"/api/cv-upload/{uploaded['upload_id']}", headers=header_a)
        self.assertEqual(visible.status_code, 200)
        self.assertNotIn(_SECRET, visible.text)

        self.assertEqual(self.client.get("/api/employer/jobs/job-a", headers=header_b).status_code, 404)
        self.assertEqual(self.client.get("/api/employer/jobs/job-a", headers=header_a).status_code, 200)
        public_jobs = self.client.get("/api/jobs")
        self.assertEqual(public_jobs.status_code, 200)
        self.assertNotIn("description", public_jobs.text)
        self.assertNotIn("criteria", public_jobs.text)

        summary = self.client.get(f"/api/employer/matching-summary/{uploaded['upload_id']}", headers=header_a)
        self.assertEqual(summary.status_code, 200)
        self.assertNotIn("reasoning", summary.text)
        self.assertNotIn("missing_requirements", summary.text)
        self.assertNotIn(_SECRET, summary.text)

    def test_unauthenticated_routes_hide_stored_text(self) -> None:
        owner = self._signup("owner@example.com", "Owner")
        self._job(owner["employer"]["id"], "job-owner")
        uploaded = self._upload("job-owner")
        for path in (
            "/api/employer/jobs",
            "/api/employer/results",
            f"/api/employer/proof-result/{uploaded['upload_id']}",
            f"/api/cv-upload/{uploaded['upload_id']}",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertNotIn(_SECRET, response.text)
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)

    def test_upload_validation(self) -> None:
        owner = self._signup("files@example.com", "Files")
        self._job(owner["employer"]["id"], "job-files")
        missing = self.client.post(
            "/api/upload-cv",
            files={"file": ("cv.pdf", b"%PDF-1.4", "application/pdf")},
        )
        self.assertEqual(missing.status_code, 422)
        not_pdf = self.client.post(
            "/api/upload-cv",
            data={"job_id": "job-files"},
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(not_pdf.status_code, 422)
        bad_magic = self.client.post(
            "/api/upload-cv",
            data={"job_id": "job-files"},
            files={"file": ("cv.pdf", b"not-a-pdf", "application/pdf")},
        )
        self.assertEqual(bad_magic.status_code, 422)

        calls = {"count": 0}
        original = cv_processing.extract_text_from_pdf

        def counting_pdf(pdf_content: bytes) -> str:
            calls["count"] += 1
            return original(pdf_content)

        cv_processing.extract_text_from_pdf = counting_pdf
        oversized = b"%PDF-" + (b"A" * 2_000_000)
        too_big = self.client.post(
            "/api/upload-cv",
            data={"job_id": "job-files"},
            files={"file": ("big.pdf", oversized, "application/pdf")},
        )
        self.assertEqual(too_big.status_code, 422)
        self.assertEqual(calls["count"], 0)
        self.assertIn("2 MB", too_big.text)

    def test_login_and_cors_parser(self) -> None:
        created = self._signup("login@example.com", "Login")
        bad = self.client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "wrong-password-1"},
        )
        self.assertEqual(bad.status_code, 401)
        good = self.client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": _PASSWORD},
        )
        self.assertEqual(good.status_code, 200)
        self.assertNotEqual(good.json()["token"], created["token"])
        me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {good.json()['token']}"})
        self.assertEqual(me.json()["id"], created["employer"]["id"])
        duplicate = self.client.post(
            "/api/auth/signup",
            json={"email": "login@example.com", "password": _PASSWORD, "display_name": "Again"},
        )
        self.assertEqual(duplicate.status_code, 409)
        with self.assertRaises(RuntimeError):
            parse_cors_origins("*")
        with self.assertRaises(RuntimeError):
            parse_cors_origins("http://localhost:3000,*")
        self.assertEqual(parse_cors_origins(None)[0], "http://localhost:3000")

    def test_health_reports_sqlite_without_a_secret(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["persistence"], "sqlite")
        self.assertNotIn("postgres://", response.text)
        self.assertNotIn("postgresql://", response.text)


class AIServiceAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.saved_token = os.environ.get("AI_SERVICE_TOKEN")
        self.saved_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ.pop("AI_SERVICE_TOKEN", None)
        os.environ["ANTHROPIC_API_KEY"] = ""
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self.saved_token is None:
            os.environ.pop("AI_SERVICE_TOKEN", None)
        else:
            os.environ["AI_SERVICE_TOKEN"] = self.saved_token
        if self.saved_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = self.saved_key

    def test_extract_rejects_missing_and_wrong_token(self) -> None:
        from ai_service.app.main import app as ai_app

        client = TestClient(ai_app)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertIs(health.json()["auth_configured"], False)
        self.assertNotIn("anthropic_api_key", health.text)
        open_extract = client.post("/extract", json={"cv_text": "Python developer"})
        self.assertEqual(open_extract.status_code, 503)
        os.environ["AI_SERVICE_TOKEN"] = "unit-test-token"
        denied = client.post(
            "/extract",
            json={"cv_text": "Python developer"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(denied.status_code, 401)
        allowed = client.post(
            "/extract",
            json={"cv_text": "Python developer"},
            headers={"Authorization": "Bearer unit-test-token"},
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertNotIn("unit-test-token", allowed.text)
        self.assertIn("python", allowed.json()["skills"])


if __name__ == "__main__":
    unittest.main()
