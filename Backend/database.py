"""Employer-scoped persistence.

SQLite is the local and test backend. Set DATABASE_URL to a Postgres
connection string, such as Supabase, to keep rows across a restart.
Importing this module does not create a database file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from Backend.models import Job, JobCriteria, VerificationStatus
from Backend.store import Store

_MIN_BOOTSTRAP_PASSWORD = 12


def _job_from_row(row: dict) -> Job:
    return Job(
        job_id=row["job_id"],
        title=row["title"],
        company=row["company"],
        description=row["description"],
        criteria=JobCriteria(**row["criteria"]),
        verification_status=VerificationStatus(row["verification_status"]),
        is_active=bool(row["is_active"]),
    )


class Database:
    def __init__(self) -> None:
        self._store: Store | None = None

    def use_sqlite_for_tests(self, path: str) -> None:
        store = Store(sqlite_path=path)
        store.ensure_schema()
        self._seed(store)
        self._store = store

    @property
    def store(self) -> Store:
        if self._store is None:
            store = Store.from_env()
            store.ensure_schema()
            self._seed(store)
            self._store = store
        return self._store

    def _seed(self, store: Store) -> None:
        email = os.environ.get("EMPLOYER_BOOTSTRAP_EMAIL", "").strip().lower()
        password = os.environ.get("EMPLOYER_BOOTSTRAP_PASSWORD", "")
        if not email or len(password) < _MIN_BOOTSTRAP_PASSWORD:
            return
        display_name = os.environ.get("EMPLOYER_BOOTSTRAP_NAME", "").strip() or "VeriHire jobs"
        employer = store.ensure_employer(email=email, password=password, display_name=display_name)
        seed_path = Path(__file__).parent / "data" / "seed_jobs.json"
        if not seed_path.exists():
            return
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
        for job_data in payload.get("jobs", []):
            store.ensure_job(
                {
                    "job_id": job_data["job_id"],
                    "employer_id": employer["employer_id"],
                    "title": job_data["title"],
                    "company": job_data["company"],
                    "description": job_data["description"],
                    "criteria": job_data["criteria"],
                    "verification_status": job_data["verification_status"],
                    "is_active": job_data.get("is_active", True),
                }
            )

    def get_job(self, job_id: str) -> Job:
        row = self.store.get_job(job_id)
        if row is None:
            raise ValueError("Job not found")
        return _job_from_row(row)

    def get_job_owner(self, job_id: str) -> str | None:
        row = self.store.get_job(job_id)
        if row is None:
            return None
        return str(row["employer_id"])

    def list_jobs_for_employer(self, employer_id: str) -> list[Job]:
        return [_job_from_row(row) for row in self.store.list_jobs(employer_id)]

    def list_public_jobs(self) -> list[dict[str, str]]:
        return [
            {"job_id": row["job_id"], "title": row["title"], "company": row["company"]}
            for row in self.store.list_jobs()
        ]

    def save_cv_upload(self, upload_data: dict) -> str:
        employer_id = upload_data.get("employer_id")
        job_id = upload_data.get("job_id")
        upload_id = upload_data.get("upload_id")
        if not isinstance(employer_id, str) or not employer_id:
            raise ValueError("Upload is missing an employer")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("Upload is missing a job")
        if not isinstance(upload_id, str) or not upload_id:
            raise ValueError("Upload is missing an id")
        self.store.save_upload(upload_data)
        return upload_id

    def get_cv_upload(self, upload_id: str) -> dict:
        row = self.store.get_upload(upload_id)
        if row is None:
            raise ValueError("Upload not found")
        return row

    def list_uploads_for_employer(self, employer_id: str) -> list[dict]:
        return self.store.list_uploads(employer_id)


db = Database()
