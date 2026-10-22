"""Two-process persistence check for an empty Postgres database.

Run from the repository root:

    python -m Backend.scripts.check_postgres_persistence write
    python -m Backend.scripts.check_postgres_persistence verify

verify must be a new Python process. It reads the sentinel and then removes
only rows that carry this test's markers. cleanup removes those same rows
when write stops halfway. Neither command deletes a row that fails the marker
check, and neither prints DATABASE_URL.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import parse_qs, urlparse

from Backend.store import Store

EMAIL = "verihire-persistence-check@example.com"
DISPLAY_NAME = "VeriHire persistence check"
JOB_ID = "verihire-persistence-check-job"
UPLOAD_ID = "verihire-persistence-check-upload"
SENTINEL_TEXT = "SENTINEL-NOT-A-CV"
JOB_TITLE = "Persistence check"
JOB_COMPANY = "VeriHire persistence check"
JOB_DESCRIPTION = "verihire-persistence-check-sentinel"
_PASSWORD = "persistence-check-pass"

_ALLOWED_TABLES = frozenset({"employers", "sessions", "jobs", "cv_uploads"})
_BLOCKED_REFS = (
    "avmnuioolxkqurzwfhgg",
    "rmmxkgiebjdvoincvabe",
    "hxhkygxpeuoinfzdzrtz",
)
_DELETE_UPLOAD = """
DELETE FROM cv_uploads
WHERE upload_id = ?
  AND employer_id = ?
  AND job_id = ?
  AND extracted_text = ?
"""
_DELETE_SESSIONS = """
DELETE FROM sessions
WHERE employer_id = ?
  AND employer_id IN (
    SELECT employer_id FROM employers
    WHERE employer_id = ? AND email = ? AND display_name = ?
  )
"""
_DELETE_JOB = """
DELETE FROM jobs
WHERE job_id = ?
  AND employer_id = ?
  AND title = ?
  AND company = ?
  AND description = ?
"""
_DELETE_EMPLOYER = """
DELETE FROM employers
WHERE employer_id = ?
  AND email = ?
  AND display_name = ?
"""


@dataclass(frozen=True)
class Presence:
    employer_owned: bool = False
    employer_foreign: bool = False
    job_owned: bool = False
    job_foreign: bool = False
    upload_owned: bool = False
    upload_foreign: bool = False

    def lines(self) -> list[str]:
        return [
            f"sentinel employer: {_flag(self.employer_owned, self.employer_foreign)}",
            f"sentinel job: {_flag(self.job_owned, self.job_foreign)}",
            f"sentinel upload: {_flag(self.upload_owned, self.upload_foreign)}",
        ]


def _flag(owned: bool, foreign: bool) -> str:
    if foreign:
        return "blocked by a different existing row"
    if owned:
        return "present"
    return "absent"


def validate_database_url(url: str) -> str:
    """Return a fixed refusal, or an empty string when the URL may be used."""
    if not url or not url.startswith("postgres"):
        return "DATABASE_URL is unset or is not a postgres URL"
    lowered = url.lower()
    if any(ref in lowered for ref in _BLOCKED_REFS) or "supabase.co" in lowered or "pooler.supabase.com" in lowered:
        return "Refusing a Supabase connection"
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return "DATABASE_URL has no host"
    if "-pooler" in host or host.startswith("pooler."):
        return "Refusing a pooled connection host"
    if parsed.port == 6543:
        return "Refusing transaction-pooler port 6543"
    pooled = parse_qs(parsed.query).get("pgbouncer", ["false"])[0].lower()
    if pooled in {"1", "true", "yes"}:
        return "Refusing a pooled connection"
    return ""


def unexpected_public_tables(names: set[str]) -> str:
    """Allow an empty public schema or exactly the four VeriHire tables."""
    if not names or names == _ALLOWED_TABLES:
        return ""
    found = ", ".join(sorted(names))
    return (
        "Refusing unexpected public tables. "
        f"Found: {found}. Expected no tables, or only employers, sessions, jobs, and cv_uploads. "
        "No sentinel changes were made."
    )


def inconsistent(presence: Presence) -> bool:
    if (presence.job_owned or presence.upload_owned) and not presence.employer_owned:
        return True
    if presence.upload_owned and not presence.job_owned:
        return True
    return False


def decide_write(presence: Presence) -> str:
    if presence.employer_foreign or presence.job_foreign or presence.upload_foreign or inconsistent(presence):
        return "foreign"
    owned = (presence.employer_owned, presence.job_owned, presence.upload_owned)
    if owned == (True, True, True):
        return "complete"
    if any(owned):
        return "partial"
    return "create"


def decide_cleanup(presence: Presence) -> str:
    if presence.employer_foreign or presence.job_foreign or presence.upload_foreign or inconsistent(presence):
        return "refuse"
    if presence.employer_owned or presence.job_owned or presence.upload_owned:
        return "delete-owned"
    return "none"


def owned_delete_plan(presence: Presence) -> tuple[str, ...]:
    if decide_cleanup(presence) != "delete-owned":
        return ()
    steps: list[str] = []
    if presence.upload_owned:
        steps.append("cv_uploads")
    if presence.employer_owned:
        steps.append("sessions")
    if presence.job_owned:
        steps.append("jobs")
    if presence.employer_owned:
        steps.append("employers")
    return tuple(steps)


def safe_failure(exc: BaseException) -> str:
    """Exception class only. Database messages can contain a connection string."""
    return f"{exc.__class__.__name__}: database operation failed"


def _job_criteria() -> dict[str, object]:
    return {
        "required_skills": {},
        "min_years_experience": 0,
        "education_level": None,
        "languages": [],
        "certifications": [],
    }


def _execute(store: Store, sql: str, params: tuple[object, ...]) -> list[Mapping[str, object]]:
    with store.connection() as conn:
        cursor = store._run(conn, sql, params)
        if cursor.description is None:
            return []
        return list(cursor.fetchall())


def _schema_problem(store: Store) -> str:
    rows = _execute(store, "SELECT current_schema() AS current_schema", ())
    current = str(rows[0]["current_schema"] or "")
    if current != "public":
        return "Refusing a connection whose current schema is not public. No sentinel changes were made."
    tables = _execute(
        store,
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """,
        (),
    )
    return unexpected_public_tables({str(row["table_name"]) for row in tables})


def _presence(store: Store) -> Presence:
    employer = store.get_employer_by_email(EMAIL)
    employer_owned = False
    employer_foreign = False
    employer_id = ""
    if employer is not None:
        employer_owned = employer["display_name"] == DISPLAY_NAME and employer["email"] == EMAIL
        employer_foreign = not employer_owned
        employer_id = str(employer["employer_id"])

    job = store.get_job(JOB_ID)
    job_owned = False
    job_foreign = False
    if job is not None:
        job_owned = (
            employer_owned
            and job["employer_id"] == employer_id
            and job["title"] == JOB_TITLE
            and job["company"] == JOB_COMPANY
            and job["description"] == JOB_DESCRIPTION
        )
        job_foreign = not job_owned

    upload = store.get_upload(UPLOAD_ID)
    upload_owned = False
    upload_foreign = False
    if upload is not None:
        upload_owned = (
            job_owned
            and upload["employer_id"] == employer_id
            and upload["job_id"] == JOB_ID
            and upload["extracted_text"] == SENTINEL_TEXT
        )
        upload_foreign = not upload_owned
    return Presence(
        employer_owned=employer_owned,
        employer_foreign=employer_foreign,
        job_owned=job_owned,
        job_foreign=job_foreign,
        upload_owned=upload_owned,
        upload_foreign=upload_foreign,
    )


def _report(presence: Presence) -> None:
    for line in presence.lines():
        print(line)


def _resume_hint() -> None:
    print("No broad delete was performed.")
    print("Inspect with: python -m Backend.scripts.check_postgres_persistence status")
    print("Remove only marked sentinel rows with: python -m Backend.scripts.check_postgres_persistence cleanup")
    print("After cleanup reports that nothing remains, run write again in this environment.")


def _delete_owned(store: Store, presence: Presence) -> dict[str, int]:
    """Delete marked rows only. The WHERE clauses repeat the markers."""
    if decide_cleanup(presence) != "delete-owned" or not presence.employer_owned:
        return {}
    employer = store.get_employer_by_email(EMAIL)
    if employer is None or employer["display_name"] != DISPLAY_NAME:
        return {}
    employer_id = employer["employer_id"]
    counts = {"cv_uploads": 0, "sessions": 0, "jobs": 0, "employers": 0}
    with store.connection() as conn:
        if presence.upload_owned:
            counts["cv_uploads"] = store._run(
                conn,
                _DELETE_UPLOAD,
                (UPLOAD_ID, employer_id, JOB_ID, SENTINEL_TEXT),
            ).rowcount
        counts["sessions"] = store._run(
            conn,
            _DELETE_SESSIONS,
            (employer_id, employer_id, EMAIL, DISPLAY_NAME),
        ).rowcount
        if presence.job_owned:
            counts["jobs"] = store._run(
                conn,
                _DELETE_JOB,
                (JOB_ID, employer_id, JOB_TITLE, JOB_COMPANY, JOB_DESCRIPTION),
            ).rowcount
        counts["employers"] = store._run(
            conn,
            _DELETE_EMPLOYER,
            (employer_id, EMAIL, DISPLAY_NAME),
        ).rowcount
    return {name: int(count) for name, count in counts.items()}


def _prepare(store: Store) -> str:
    problem = _schema_problem(store)
    if problem:
        return problem
    store.ensure_schema()
    return _schema_problem(store)


def _open_store() -> Store | int:
    url = os.environ.get("DATABASE_URL", "").strip()
    problem = validate_database_url(url)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    try:
        store = Store(database_url=url)
        problem = _prepare(store)
    except Exception as exc:
        print(safe_failure(exc), file=sys.stderr)
        print("No sentinel delete was performed.", file=sys.stderr)
        return 1
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return store


def command_status(store: Store) -> int:
    presence = _presence(store)
    _report(presence)
    if decide_write(presence) == "foreign" or decide_cleanup(presence) == "refuse":
        print("A sentinel key is already used by a different row. Nothing was changed.")
        return 3
    return 0


def command_write(store: Store) -> int:
    presence = _presence(store)
    decision = decide_write(presence)
    if decision == "foreign":
        _report(presence)
        print("Nothing was inserted or deleted.")
        return 3
    if decision == "complete":
        _report(presence)
        print("Sentinel is already complete. Do not write again.")
        print("In a new Python process run: python -m Backend.scripts.check_postgres_persistence verify")
        return 0
    if decision == "partial":
        _report(presence)
        print("Write stopped because a previous attempt left some marked rows.")
        _resume_hint()
        return 4
    try:
        employer = store.create_employer(email=EMAIL, password=_PASSWORD, display_name=DISPLAY_NAME)
        store.insert_job(
            {
                "job_id": JOB_ID,
                "employer_id": employer["employer_id"],
                "title": JOB_TITLE,
                "company": JOB_COMPANY,
                "description": JOB_DESCRIPTION,
                "criteria": _job_criteria(),
                "verification_status": "unverified",
                "is_active": True,
            }
        )
        store.save_upload(
            {
                "upload_id": UPLOAD_ID,
                "employer_id": employer["employer_id"],
                "job_id": JOB_ID,
                "cv_source": "pdf",
                "extracted_text": SENTINEL_TEXT,
                "extracted_data": {},
                "matching_results": [],
                "proof_results": [],
            }
        )
    except Exception as exc:
        print(safe_failure(exc), file=sys.stderr)
        try:
            _report(_presence(store))
        except Exception as report_exc:
            print(safe_failure(report_exc), file=sys.stderr)
        _resume_hint()
        return 1
    print("Created sentinel employer, job, and upload.")
    print("Stop this process. In a new Python process run:")
    print("  python -m Backend.scripts.check_postgres_persistence verify")
    print("verify checks that the sentinel is still there, then removes only those marked rows.")
    return 0


def command_verify(store: Store) -> int:
    presence = _presence(store)
    if decide_write(presence) == "foreign" or inconsistent(presence):
        _report(presence)
        print("Nothing was deleted.")
        return 3
    if decide_write(presence) == "partial":
        _report(presence)
        print("The sentinel is incomplete, so this is not a persistence proof.")
        _resume_hint()
        return 4
    if decide_write(presence) != "complete":
        _report(presence)
        print("Nothing was deleted. Run write before verify.")
        return 4
    print("Sentinel was readable in this new process.")
    result = _finish_cleanup(store, presence)
    if result == 0:
        print("persisted across a new process, sentinel removed")
    return result


def command_cleanup(store: Store) -> int:
    presence = _presence(store)
    if decide_cleanup(presence) == "refuse":
        _report(presence)
        print("Nothing was deleted.")
        return 3
    if decide_cleanup(presence) == "none":
        _report(presence)
        print("No marked sentinel rows were present.")
        return 0
    result = _finish_cleanup(store, presence)
    if result == 0:
        print("Marked sentinel rows were removed. No other rows were deleted.")
    return result


def _finish_cleanup(store: Store, presence: Presence) -> int:
    plan = owned_delete_plan(presence)
    try:
        counts = _delete_owned(store, presence)
    except Exception as exc:
        print(safe_failure(exc), file=sys.stderr)
        print("Cleanup stopped. Run status before trying cleanup again. No unqualified delete was used.")
        return 1
    deleted = ", ".join(f"{name}={counts.get(name, 0)}" for name in plan) or "none"
    print(f"Removed marked rows: {deleted}")
    remainder = _presence(store)
    _report(remainder)
    if decide_cleanup(remainder) != "none":
        print("Marked or blocking rows remain. Nothing further was deleted.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"write", "verify", "cleanup", "status"}:
        print(
            "Usage: python -m Backend.scripts.check_postgres_persistence "
            "{write|verify|cleanup|status}",
            file=sys.stderr,
        )
        print("write and verify are two separate process runs. cleanup deletes only marked sentinel rows.")
        return 2
    opened = _open_store()
    if isinstance(opened, int):
        return opened
    command = argv[1]
    if command == "status":
        return command_status(opened)
    if command == "write":
        return command_write(opened)
    if command == "verify":
        return command_verify(opened)
    return command_cleanup(opened)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
