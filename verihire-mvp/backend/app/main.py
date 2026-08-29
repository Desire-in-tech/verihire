"""
What this file does
--------------------
The entry point for the backend/API service. It:

  1. Creates the FastAPI app and wires up the three route groups
     (jobs, candidates, employers) from routes/.
  2. Loads the seed job listings from data/jobs_seed.json into the
     in-memory store on startup, so GET /jobs returns something useful
     immediately without needing to POST any jobs first.

This is the service your teammate owns and will likely rewrite pieces of
(especially store.py, if a real database gets added) - the routes/ files
are written so each one only depends on store.py, ai_client.py,
rules_engine.py, midnight_mock.py and employer_verification.py, so they can
be extended independently without touching this file much.

Run it directly with:  uvicorn app.main:app --reload --port 8000
(run from inside the backend/ directory, with its virtualenv active, and
with the AI service already running on port 8001)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .config import settings
from .routes import candidates, employers, jobs

app = FastAPI(
    title="VeriHire Backend API",
    description="Ties the candidate, job, rules-engine, and mock-Midnight pieces together.",
)

# Lets the static pages in frontend/ (opened straight from disk or served
# with a plain `python -m http.server`) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(employers.router)


@app.on_event("startup")
def on_startup():
    store.load_seed_jobs()


@app.get("/health")
def health():
    return {"status": "ok", "jobs_loaded": len(store.list_jobs())}
