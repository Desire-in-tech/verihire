"""SQLite for local tests and Postgres when DATABASE_URL is set.

Render's free web disk is ephemeral. A Postgres URL, such as a Supabase
connection string, is what keeps employer results across a restart.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from Backend.security import (
    dummy_verify,
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)

_MIGRATION = Path(__file__).parent / "migrations" / "001_employer_persistence.sql"
_SESSION_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class Store:
    def __init__(self, *, database_url: str | None = None, sqlite_path: str | None = None) -> None:
        self.database_url = database_url or None
        self.sqlite_path = sqlite_path
        self.backend_name = "postgres" if self.database_url else "sqlite"
        if not self.database_url and not self.sqlite_path:
            raise ValueError("A database URL or SQLite path is required")

    @classmethod
    def from_env(cls) -> "Store":
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if database_url.startswith("postgres"):
            return cls(database_url=database_url)
        path = os.environ.get("VERIHIRE_DB_PATH", "").strip()
        if not path:
            path = str(Path(__file__).parent / ".local" / "verihire.sqlite")
        return cls(sqlite_path=path)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        if self.database_url:
            import psycopg
            from psycopg.rows import dict_row

            conn = psycopg.connect(self.database_url, connect_timeout=10, row_factory=dict_row)
        else:
            Path(self.sqlite_path or "").parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.sqlite_path or "")
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _run(self, conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
        statement = sql if self.database_url is None else sql.replace("?", "%s")
        return conn.execute(statement, params)

    def ensure_schema(self) -> None:
        script = _MIGRATION.read_text(encoding="utf-8")
        lines = [
            line
            for line in script.splitlines()
            if not line.strip().startswith("--")
        ]
        statements = [part.strip() for part in "\n".join(lines).split(";") if part.strip()]
        with self.connection() as conn:
            for statement in statements:
                self._run(conn, statement)

    def create_employer(self, *, email: str, password: str, display_name: str) -> dict[str, str]:
        import uuid

        employer_id = str(uuid.uuid4())
        with self.connection() as conn:
            self._run(
                conn,
                """
                INSERT INTO employers (employer_id, email, password_hash, display_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (employer_id, email, hash_password(password), display_name, _iso(_utcnow())),
            )
        return {"employer_id": employer_id, "email": email, "display_name": display_name}

    def ensure_employer(self, *, email: str, password: str, display_name: str) -> dict[str, str]:
        existing = self.get_employer_by_email(email)
        if existing:
            return existing
        return self.create_employer(email=email, password=password, display_name=display_name)

    def get_employer_by_email(self, email: str) -> dict[str, str] | None:
        with self.connection() as conn:
            row = self._run(
                conn,
                "SELECT employer_id, email, display_name FROM employers WHERE email = ?",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return {"employer_id": row["employer_id"], "email": row["email"], "display_name": row["display_name"]}

    def authenticate(self, email: str, password: str) -> dict[str, str] | None:
        with self.connection() as conn:
            row = self._run(
                conn,
                "SELECT employer_id, email, display_name, password_hash FROM employers WHERE email = ?",
                (email,),
            ).fetchone()
        if row is None:
            dummy_verify(password)
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        return {"employer_id": row["employer_id"], "email": row["email"], "display_name": row["display_name"]}

    def create_session(self, employer_id: str) -> str:
        token, token_hash = new_session_token()
        expires = _iso(_utcnow() + timedelta(days=_SESSION_DAYS))
        with self.connection() as conn:
            self._run(
                conn,
                "INSERT INTO sessions (token_hash, employer_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, employer_id, expires),
            )
        return token

    def employer_for_token(self, token: str) -> dict[str, str] | None:
        if not token:
            return None
        now = _iso(_utcnow())
        with self.connection() as conn:
            row = self._run(
                conn,
                """
                SELECT employers.employer_id, employers.email, employers.display_name
                FROM sessions
                JOIN employers ON employers.employer_id = sessions.employer_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (hash_session_token(token), now),
            ).fetchone()
        if row is None:
            return None
        return {"employer_id": row["employer_id"], "email": row["email"], "display_name": row["display_name"]}

    def insert_job(self, job: dict[str, Any]) -> None:
        with self.connection() as conn:
            self._run(
                conn,
                """
                INSERT INTO jobs (
                  job_id, employer_id, title, company, description,
                  criteria_json, verification_status, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"],
                    job["employer_id"],
                    job["title"],
                    job["company"],
                    job["description"],
                    json.dumps(job["criteria"]),
                    job["verification_status"],
                    1 if job.get("is_active", True) else 0,
                ),
            )

    def ensure_job(self, job: dict[str, Any]) -> None:
        if self.get_job(job["job_id"]) is None:
            self.insert_job(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = self._run(conn, "SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return None if row is None else self._job_row(row)

    def list_jobs(self, employer_id: str | None = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            if employer_id is None:
                rows = self._run(
                    conn,
                    "SELECT * FROM jobs WHERE is_active = 1 ORDER BY job_id",
                ).fetchall()
            else:
                rows = self._run(
                    conn,
                    "SELECT * FROM jobs WHERE employer_id = ? AND is_active = 1 ORDER BY job_id",
                    (employer_id,),
                ).fetchall()
        return [self._job_row(row) for row in rows]

    def save_upload(self, upload: dict[str, Any]) -> None:
        with self.connection() as conn:
            self._run(
                conn,
                """
                INSERT INTO cv_uploads (
                  upload_id, employer_id, job_id, cv_source, extracted_text,
                  extracted_data_json, matching_results_json, proof_results_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    upload["upload_id"],
                    upload["employer_id"],
                    upload["job_id"],
                    upload.get("cv_source", "pdf"),
                    upload.get("extracted_text", ""),
                    json.dumps(upload["extracted_data"]),
                    json.dumps(upload["matching_results"]),
                    json.dumps(upload["proof_results"]),
                    upload.get("created_at") or _iso(_utcnow()),
                ),
            )

    def get_upload(self, upload_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = self._run(conn, "SELECT * FROM cv_uploads WHERE upload_id = ?", (upload_id,)).fetchone()
        return None if row is None else self._upload_row(row)

    def list_uploads(self, employer_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = self._run(
                conn,
                "SELECT * FROM cv_uploads WHERE employer_id = ? ORDER BY created_at",
                (employer_id,),
            ).fetchall()
        return [self._upload_row(row) for row in rows]

    def _job_row(self, row: Any) -> dict[str, Any]:
        return {
            "job_id": row["job_id"],
            "employer_id": row["employer_id"],
            "title": row["title"],
            "company": row["company"],
            "description": row["description"],
            "criteria": json.loads(row["criteria_json"]),
            "verification_status": row["verification_status"],
            "is_active": bool(row["is_active"]),
        }

    def _upload_row(self, row: Any) -> dict[str, Any]:
        return {
            "upload_id": row["upload_id"],
            "employer_id": row["employer_id"],
            "job_id": row["job_id"],
            "cv_source": row["cv_source"],
            "extracted_text": row["extracted_text"],
            "extracted_data": json.loads(row["extracted_data_json"]),
            "matching_results": json.loads(row["matching_results_json"]),
            "proof_results": json.loads(row["proof_results_json"]),
            "created_at": row["created_at"],
        }
