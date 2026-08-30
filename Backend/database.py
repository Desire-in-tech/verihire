"""
A deliberately simple "database": plain Python dictionaries held in
memory, seeded from data/seed_jobs.json on startup. Everything resets when
the process restarts - fine for a demo, not for production (see README's
future-enhancements list for swapping this out for SQLite/Postgres).

Jobs, candidates, and applications are the three tables. Routes only ever
call functions on the shared `db` instance below - nothing else in the
codebase touches these dicts directly.
"""

import json
import uuid
from pathlib import Path

from models import ApplicationResult, CandidateProfile, JobPosting


class Database:
    """Simple in-memory database backed by a JSON file for seed jobs."""

    def __init__(self):
        self.jobs: dict[str, JobPosting] = {}
        self.candidates: dict[str, CandidateProfile] = {}
        self.applications: dict[tuple[str, str], ApplicationResult] = {}  # (candidate_id, job_id) -> result
        self._candidate_counter = 100  # feeds the "PX-104" style anonymized refs
        self._load_seed_data()

    def _load_seed_data(self):
        """Load jobs from seed JSON file."""
        seed_path = Path(__file__).parent / "data" / "seed_jobs.json"
        if seed_path.exists():
            with open(seed_path, 'r') as f:
                raw_jobs = json.load(f)
                for raw in raw_jobs:
                    job = JobPosting.model_validate(raw)
                    self.jobs[job.job_id] = job

    def new_id(self) -> str:
        return str(uuid.uuid4())

    def next_anonymized_ref(self) -> str:
        self._candidate_counter += 1
        return f"PX-{self._candidate_counter}"

    # --- Jobs -------------------------------------------------------------

    def save_job(self, job: JobPosting) -> None:
        self.jobs[job.job_id] = job

    def get_job(self, job_id: str) -> JobPosting:
        """Get a job by ID."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        return self.jobs[job_id]

    def get_all_jobs(self) -> list[JobPosting]:
        """Get all active jobs."""
        return [job for job in self.jobs.values() if job.is_active]

    # --- Candidates ---------------------------------------------------------

    def save_candidate(self, candidate: CandidateProfile) -> None:
        self.candidates[candidate.candidate_id] = candidate

    def get_candidate(self, candidate_id: str) -> CandidateProfile:
        if candidate_id not in self.candidates:
            raise ValueError(f"Candidate {candidate_id} not found")
        return self.candidates[candidate_id]

    # --- Applications ---------------------------------------------------------

    def save_application(self, candidate_id: str, job_id: str, result: ApplicationResult) -> None:
        self.applications[(candidate_id, job_id)] = result

    def get_application(self, candidate_id: str, job_id: str) -> ApplicationResult:
        key = (candidate_id, job_id)
        if key not in self.applications:
            raise ValueError(f"No application found for candidate {candidate_id} on job {job_id}")
        return self.applications[key]

    def list_applications_for_job(self, job_id: str) -> list[ApplicationResult]:
        return [result for (_, jid), result in self.applications.items() if jid == job_id]


# Global database instance
db = Database()
