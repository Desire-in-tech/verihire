"""Safety checks for the Postgres persistence script. No database connection."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from Backend.scripts.check_postgres_persistence import (
    Presence,
    _DELETE_EMPLOYER,
    _DELETE_JOB,
    _DELETE_SESSIONS,
    _DELETE_UPLOAD,
    decide_cleanup,
    decide_write,
    owned_delete_plan,
    safe_failure,
    unexpected_public_tables,
    validate_database_url,
)

_PASSWORD = "super-secret-token"
_DIRECT = f"postgresql://owner:{_PASSWORD}@ep-example.c-1.us-east-1.aws.neon.tech/neondb?sslmode=require"


class UrlRefusalTests(unittest.TestCase):
    def test_direct_neon_url_is_allowed(self) -> None:
        self.assertEqual(validate_database_url(_DIRECT), "")

    def test_refusals_do_not_echo_the_url_or_password(self) -> None:
        samples = [
            "",
            "sqlite:///tmp/test.sqlite",
            f"postgresql://postgres:{_PASSWORD}@db.avmnuioolxkqurzwfhgg.supabase.co:5432/postgres",
            f"postgresql://postgres.rmmxkgiebjdvoincvabe:{_PASSWORD}@aws-0-eu-west-1.pooler.supabase.com:5432/postgres",
            f"postgresql://postgres:{_PASSWORD}@db.hxhkygxpeuoinfzdzrtz.supabase.co:5432/postgres",
            f"postgresql://owner:{_PASSWORD}@ep-example-pooler.c-1.us-east-1.aws.neon.tech/neondb",
            f"postgresql://owner:{_PASSWORD}@ep-example.c-1.us-east-1.aws.neon.tech:6543/neondb",
            f"postgresql://owner:{_PASSWORD}@ep-example.c-1.us-east-1.aws.neon.tech/neondb?pgbouncer=true",
        ]
        for sample in samples:
            message = validate_database_url(sample)
            self.assertTrue(message, sample.split("@")[-1])
            self.assertNotIn(_PASSWORD, message)
            self.assertNotIn("postgresql://", message)
            self.assertNotIn("avmnuioolxkqurzwfhgg", message)
            self.assertNotIn("rmmxkgiebjdvoincvabe", message)

    def test_process_refusal_does_not_print_the_secret(self) -> None:
        env = os.environ.copy()
        env["DATABASE_URL"] = (
            f"postgresql://postgres:{_PASSWORD}@db.avmnuioolxkqurzwfhgg.supabase.co:5432/postgres"
        )
        completed = subprocess.run(
            [sys.executable, "-m", "Backend.scripts.check_postgres_persistence", "write"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        combined = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn(_PASSWORD, combined)
        self.assertNotIn("postgresql://", combined)
        self.assertIn("Refusing a Supabase connection", combined)


class SchemaAndCleanupPlanTests(unittest.TestCase):
    def test_only_empty_or_exact_verihire_tables_are_accepted(self) -> None:
        self.assertEqual(unexpected_public_tables(set()), "")
        self.assertEqual(
            unexpected_public_tables({"employers", "sessions", "jobs", "cv_uploads"}),
            "",
        )
        partial = unexpected_public_tables({"employers", "jobs"})
        self.assertIn("Refusing unexpected public tables", partial)
        occupied = unexpected_public_tables({"organizations", "users"})
        self.assertIn("organizations", occupied)
        self.assertIn("No sentinel changes were made", occupied)

    def test_cleanup_plan_never_includes_a_foreign_or_absent_row(self) -> None:
        foreign = Presence(employer_foreign=True)
        self.assertEqual(decide_write(foreign), "foreign")
        self.assertEqual(decide_cleanup(foreign), "refuse")
        self.assertEqual(owned_delete_plan(foreign), ())

        partial = Presence(employer_owned=True)
        self.assertEqual(decide_write(partial), "partial")
        self.assertEqual(owned_delete_plan(partial), ("sessions", "employers"))

        complete = Presence(employer_owned=True, job_owned=True, upload_owned=True)
        self.assertEqual(decide_write(complete), "complete")
        self.assertEqual(
            owned_delete_plan(complete),
            ("cv_uploads", "sessions", "jobs", "employers"),
        )
        self.assertEqual(decide_cleanup(Presence()), "none")
        self.assertEqual(owned_delete_plan(Presence()), ())

        mismatched_child = Presence(job_owned=True)
        self.assertEqual(decide_cleanup(mismatched_child), "refuse")
        self.assertEqual(owned_delete_plan(mismatched_child), ())

    def test_delete_statements_require_the_sentinel_markers(self) -> None:
        statements = {
            "upload": _DELETE_UPLOAD,
            "sessions": _DELETE_SESSIONS,
            "job": _DELETE_JOB,
            "employer": _DELETE_EMPLOYER,
        }
        for name, statement in statements.items():
            compact = " ".join(statement.split())
            self.assertIn("DELETE FROM", compact, name)
            self.assertIn("WHERE", compact, name)
        self.assertIn("extracted_text = ?", _DELETE_UPLOAD)
        self.assertIn("display_name = ?", _DELETE_SESSIONS)
        self.assertIn("description = ?", _DELETE_JOB)
        self.assertIn("email = ?", _DELETE_EMPLOYER)
        self.assertIn("display_name = ?", _DELETE_EMPLOYER)

    def test_failure_text_drops_connection_details(self) -> None:
        message = safe_failure(RuntimeError("password authentication failed for postgresql://owner:secret@host/db"))
        self.assertEqual(message, "RuntimeError: database operation failed")
        self.assertNotIn("secret", message)
        self.assertNotIn("postgresql://", message)


if __name__ == "__main__":
    unittest.main()
