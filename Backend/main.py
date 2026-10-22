import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from Backend.api.auth import router as auth_router
from Backend.api.cv_processing import router as cv_router
from Backend.api.employer_dashboard import router as employer_router
from Backend.database import db
from Backend.midnight_client import MidnightClient

_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def parse_cors_origins(raw: str | None = None) -> list[str]:
    """Explicit frontend origins only. A wildcard is rejected."""
    value = _DEFAULT_ORIGINS if raw is None else raw
    origins = [item.strip().rstrip("/") for item in value.split(",") if item.strip()]
    if not origins or any(origin == "*" or "*" in origin for origin in origins):
        raise RuntimeError("CORS_ORIGINS must list explicit origins and must not include *")
    return origins


def _docs_enabled() -> bool:
    return os.environ.get("ENABLE_API_DOCS", "").strip().lower() == "true"


_docs = "/docs" if _docs_enabled() else None

app = FastAPI(
    title="VeriHire API Layer",
    description="API Layer for CV processing and job matching",
    version="1.0.0",
    docs_url=_docs,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(os.environ.get("CORS_ORIGINS")),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(cv_router)
app.include_router(employer_router)


@app.get("/health")
async def health_check():
    try:
        persistence = db.store.backend_name
    except Exception:
        persistence = "unavailable"
    return {
        "status": "healthy",
        "persistence": persistence,
        "midnight_configured": MidnightClient().configured,
    }


@app.get("/midnight/health")
async def midnight_health():
    """Read-only GET of the Midnight service /health route."""
    return await MidnightClient().service_health()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
