from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.candidates import router as candidates_router
from api.jobs import router as jobs_router
from api.employers import router as employers_router

app = FastAPI(
    title="VeriHire API Layer",
    description="API Layer for CV processing, job matching, and Midnight proof verification",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(employers_router)

@app.get("/health")
async def health_check():
    from database import db
    return {"status": "healthy", "jobs_loaded": len(db.get_all_jobs())}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
