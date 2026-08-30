import json
import uuid
from pathlib import Path
from models import Job, JobCriteria, VerificationStatus

class Database:
    """Simple in-memory database backed by JSON files for seed data."""
    
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.cv_uploads: dict[str, dict] = {}
        self._load_seed_data()
    
    def _load_seed_data(self):
        """Load jobs from seed JSON file."""
        seed_path = Path(__file__).parent / "data" / "seed_jobs.json"
        if seed_path.exists():
            with open(seed_path, 'r') as f:
                data = json.load(f)
                for job_data in data.get('jobs', []):
                    job = Job(
                        job_id=job_data['job_id'],
                        title=job_data['title'],
                        company=job_data['company'],
                        description=job_data['description'],
                        criteria=JobCriteria(**job_data['criteria']),
                        verification_status=VerificationStatus(job_data['verification_status']),
                        is_active=job_data.get('is_active', True)
                    )
                    self.jobs[job.job_id] = job
    
    def get_job(self, job_id: str) -> Job:
        """Get a job by ID."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        return self.jobs[job_id]
    
    def get_all_jobs(self) -> list[Job]:
        """Get all active jobs."""
        return [job for job in self.jobs.values() if job.is_active]
    
    def save_cv_upload(self, upload_data: dict) -> str:
        """Save CV upload result and return upload ID."""
        upload_id = str(uuid.uuid4())
        self.cv_uploads[upload_id] = upload_data
        return upload_id
    
    def get_cv_upload(self, upload_id: str) -> dict:
        """Get saved CV upload result."""
        if upload_id not in self.cv_uploads:
            raise ValueError(f"Upload {upload_id} not found")
        return self.cv_uploads[upload_id]

# Global database instance
db = Database()
