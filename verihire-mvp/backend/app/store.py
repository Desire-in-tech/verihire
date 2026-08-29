"""
What this file does
--------------------
A deliberately tiny "database": plain Python dictionaries held in memory,
plus a couple of JSON-file helpers. This is enough for a hackathon MVP and
a live demo - everything resets when the process restarts, which is fine
since there's no persistence requirement yet.

If there's time before the deadline, this is the file to replace with a
real database (SQLite via SQLAlchemy is the least-effort upgrade). Nothing
in routes/ would need to change except the functions in this file, since
routes only ever call functions like `get_job`, `save_candidate`, etc.
"""

import json
import uuid
from pathlib import Path

from .models import CandidateProfile, JobPosting, ApplicationResult

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# In-memory tables.
_jobs: dict[str, JobPosting] = {}
_candidates: dict[str, CandidateProfile] = {}
_applications: dict[tuple[str, str], ApplicationResult] = {}  # (candidate_id, job_id) -> result

_candidate_counter = 100  # feeds the "PX-104" style anonymized refs


def load_seed_jobs() -> None:
    """Loads backend/data/jobs_seed.json into the in-memory jobs table on startup."""
    seed_path = _DATA_DIR / "jobs_seed.json"
    if not seed_path.exists():
        return
    raw_jobs = json.loads(seed_path.read_text())
    for raw in raw_jobs:
        job = JobPosting.model_validate(raw)
        _jobs[job.job_id] = job


def next_anonymized_ref() -> str:
    global _candidate_counter
    _candidate_counter += 1
    return f"PX-{_candidate_counter}"


def new_id() -> str:
    return str(uuid.uuid4())


# --- Jobs -------------------------------------------------------------

def save_job(job: JobPosting) -> None:
    _jobs[job.job_id] = job


def get_job(job_id: str) -> JobPosting | None:
    return _jobs.get(job_id)


def list_jobs() -> list[JobPosting]:
    return list(_jobs.values())


# --- Candidates ---------------------------------------------------------

def save_candidate(candidate: CandidateProfile) -> None:
    _candidates[candidate.candidate_id] = candidate


def get_candidate(candidate_id: str) -> CandidateProfile | None:
    return _candidates.get(candidate_id)


# --- Applications ---------------------------------------------------------

def save_application(candidate_id: str, job_id: str, result: ApplicationResult) -> None:
    _applications[(candidate_id, job_id)] = result


def get_application(candidate_id: str, job_id: str) -> ApplicationResult | None:
    return _applications.get((candidate_id, job_id))


def list_applications_for_job(job_id: str) -> list[ApplicationResult]:
    return [result for (_, jid), result in _applications.items() if jid == job_id]
