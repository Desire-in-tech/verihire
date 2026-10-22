from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from Backend.api.cv_processing import router as cv_router
from Backend.api.employer_dashboard import router as employer_router
from Backend.midnight_client import MidnightClient

app = FastAPI(
    title="VeriHire API Layer",
    description="API Layer for CV processing and job matching",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cv_router)
app.include_router(employer_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/midnight/health")
async def midnight_health():
    """Read-only GET of the Midnight service /health route."""
    return await MidnightClient().service_health()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
