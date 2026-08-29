from fastapi import APIRouter, HTTPException
from models import JobListResponse, Job, JobMatchResult
from database import db

router = APIRouter(prefix="/api/employer", tags=["employer-dashboard"])


@router.get("/jobs", response_model=JobListResponse, summary="Get all jobs")
async def get_jobs():
    """
    Get list of all active jobs for the employer dashboard.
    
    Returns:
        JobListResponse with all active jobs
    """
    try:
        jobs = db.get_all_jobs()
        return JobListResponse(
            jobs=jobs,
            total_count=len(jobs),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=Job, summary="Get job details")
async def get_job_details(job_id: str):
    """
    Get details for a specific job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Job details
    """
    try:
        job = db.get_job(job_id)
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job: {str(e)}")


@router.get("/proof-result/{upload_id}", summary="Get proof result for CV upload")
async def get_proof_result(upload_id: str):
    """
    Get the proof result from Midnight layer for a CV upload.
    Used by employer dashboard to verify applicants.
    
    Args:
        upload_id: The upload ID from CV processing
        
    Returns:
        Proof result with verification data
    """
    try:
        upload_data = db.get_cv_upload(upload_id)
        
        proof_results = upload_data.get("proof_results", [])
        if not proof_results:
            raise ValueError("No proof results found for this upload")
        
        # Return comprehensive proof data
        return {
            "upload_id": upload_id,
            "proof_results": proof_results,
            "extracted_cv_data": upload_data["extracted_data"],
            "matching_results": upload_data["matching_results"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching proof result: {str(e)}")


@router.get("/matching-summary/{upload_id}", summary="Get matching summary for CV")
async def get_matching_summary(upload_id: str):
    """
    Get a summary of how the CV matches against all jobs.
    
    Args:
        upload_id: The upload ID from CV processing
        
    Returns:
        List of job matches with scores
    """
    try:
        upload_data = db.get_cv_upload(upload_id)
        
        matching_results = upload_data.get("matching_results", [])
        
        # Format results for dashboard
        summary = []
        for result in matching_results:
            job = db.get_job(result["job_id"])
            summary.append({
                "job_id": result["job_id"],
                "job_title": job.title,
                "company": job.company,
                "matches": result["matches"],
                "score": result["score"],
                "reasoning": result["reasoning"],
                "missing_requirements": result["missing_requirements"],
            })
        
        # Sort by score descending
        summary.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "upload_id": upload_id,
            "total_jobs": len(summary),
            "matched_jobs": sum(1 for m in summary if m["matches"]),
            "matches": summary,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")
