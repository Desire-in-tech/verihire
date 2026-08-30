from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"

class JobCriteria(BaseModel):
    """Criteria that a job requires."""
    required_skills: Dict[str, int] = Field(
        default_factory=dict,
        description="Required skill -> minimum years of experience. 0 means skill must simply be present."
    )
    education_level: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class Job(BaseModel):
    """Job posting"""
    job_id: str
    title: str
    company: str
    description: str
    criteria: JobCriteria
    verification_status: VerificationStatus
    is_active: bool = True

class PDFUploadRequest(BaseModel):
    """Request to upload and process a CV from PDF"""
    filename: Optional[str] = None
    job_id: Optional[str] = None

class ExtractedCVData(BaseModel):
    """
    Structured CV data returned by the AI extraction service.

    Skills are represented as:
        skill_name -> years of experience
    """
    skills: Dict[str, int] = Field(default_factory=dict)
    education_level: Optional[str] = None
    certifications: List[str] = Field(default_factory=list)
    summary: Optional[str] = None

class RulesEngineResult(BaseModel):
    """Result of rules engine evaluation"""
    job_id: str
    matches: bool
    score: float  # 0-100
    missing_requirements: List[str]
    matched_requirements: List[str]
    reasoning: str

class ProofResult(BaseModel):
    """Result with proof from Midnight layer"""
    job_id: str
    applicant_verified: bool
    cv_data: ExtractedCVData
    matching_result: RulesEngineResult
    proof_data: Optional[Dict[str, Any]] = None  # Proof from Midnight layer

class CVUploadResponse(BaseModel):
    """Response after CV upload and processing"""
    upload_id: str
    cv_source: str = "pdf"  # 'pdf' is the primary supported source
    extracted_text: Optional[str] = None  # Raw CV text (for PDF uploads)
    extracted_data: ExtractedCVData
    matching_results: List[RulesEngineResult]
    proof_results: List[ProofResult]

class JobListResponse(BaseModel):
    """Response for job list endpoint"""
    jobs: List[Job]
    total_count: int

class JobMatchResult(BaseModel):
    """Simple result for a job match"""
    job_id: str
    job_title: str
    matches: bool
    score: float
