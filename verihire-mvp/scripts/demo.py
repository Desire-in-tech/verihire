"""
What this file does
--------------------
A runnable, end-to-end walkthrough of the whole VeriHire story from the
pitch doc, hitting the two live HTTP services with plain requests calls -
no test framework, just a script you can run during rehearsal or the
actual demo to prove the whole flow works.

Before running this, start both services in separate terminals:

    # terminal 1
    cd ai_service && uvicorn app.main:app --reload --port 8001

    # terminal 2
    cd backend && uvicorn app.main:app --reload --port 8000

Then, from the repo root:

    python scripts/demo.py

It walks through, in order:
  Scene 1 - checking a suspicious "UnknownCompany123" job first (fails verification)
  Scene 2 - checking a legitimate company (passes verification)
  Scene 3 - registering a candidate from the sample CV, applying to the
            legitimate job, and seeing the proof/checklist an employer
            would see (no personal info yet)
  Scene 4 - the candidate choosing to disclose contact info, and the
            employer's view finally including it
"""

import sys
import time
from pathlib import Path

import httpx

BACKEND = "http://localhost:8000"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _print_scene(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _print_json(label: str, data) -> None:
    import json

    print(f"\n{label}:")
    print(json.dumps(data, indent=2))


def _wait_for_backend(timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            httpx.get(f"{BACKEND}/health", timeout=2).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(0.5)
    print("Backend didn't respond on http://localhost:8000 - is it running? (see file docstring)")
    sys.exit(1)


def main() -> None:
    _wait_for_backend()

    # --- Scene 1: a suspicious job -----------------------------------
    _print_scene("Scene 1 — A suspicious job offer shows up")
    resp = httpx.post(
        f"{BACKEND}/jobs/verify-external",
        params={"company_name": "UnknownCompany123", "domain": "unknowncompany123.biz"},
    )
    verification = resp.json()
    _print_json("Employer verification result", verification)
    if verification["company_identity_verified"]:
        print("Unexpected: this should NOT be verified.")
    else:
        print("-> VeriHire says: employer verification unavailable. Don't disclose sensitive info yet.")

    # --- Scene 2: a legitimate job -------------------------------------
    _print_scene("Scene 2 — Checking a legitimate company instead")
    resp = httpx.get(f"{BACKEND}/jobs")
    jobs = resp.json()
    legit_job = next(j for j in jobs if j["domain"] == "example-technologies.com")
    _print_json(f"Job listing: {legit_job['title']} @ {legit_job['company_name']}", legit_job["verification"])
    print("-> Employer verified, recruiter verified, job verified. Safe to proceed.")

    # --- Scene 3: prove qualifications, no CV upload required ---------
    _print_scene("Scene 3 — Prove qualifications without handing over the CV")
    cv_text = (REPO_ROOT / "ai_service" / "samples" / "sample_cv.txt").read_text()
    resp = httpx.post(f"{BACKEND}/candidates", json={"cv_text": cv_text, "name": "Jordan Ellis",
                                                       "email": "jordan@example.com", "phone": "+1-555-0100"})
    candidate = resp.json()
    print(f"\nCandidate registered as anonymized ref: {candidate['anonymized_ref']}")
    print("(name/email/phone were sent, but are stored privately — not returned here)")

    resp = httpx.post(f"{BACKEND}/candidates/{candidate['candidate_id']}/apply/{legit_job['job_id']}")
    application = resp.json()
    _print_json("What the employer sees after applying (no PII)", application)
    if application["match"]["overall_match"]:
        print("-> Midnight (mocked) verifies: candidate satisfies the job's requirements.")

    # --- Scene 4: candidate chooses to disclose ------------------------
    _print_scene("Scene 4 — Employer wants to interview; candidate discloses contact info")
    resp = httpx.post(
        f"{BACKEND}/candidates/{candidate['candidate_id']}/disclose/{legit_job['job_id']}",
        params={"level": "full_disclosure"},
    )
    disclosed = resp.json()
    _print_json("Employer's view after candidate opts in to full disclosure", disclosed)

    print("\nDone — that's the full VeriHire flow, start to finish.\n")


if __name__ == "__main__":
    main()
