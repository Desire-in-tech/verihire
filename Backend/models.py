"""
Every data shape the backend works with, as Pydantic models. Three groups:

1. The shapes shared with the AI service (ExtractionResult, JobRequirements)
   - these MUST stay identical to ai_service/app/models.py. See
   SCHEMA_CONTRACT.md at the repo root - it's the single source of truth
   both sides should check before changing either copy.
2. Domain objects that only the backend owns: CandidateProfile, JobPosting,
   EmployerVerificationResult.
3. Output-only shapes produced by the rules engine and the Midnight layer
   (real or mocked): CriterionResult, MatchResult, ProofResult.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EducationLevel(str, Enum):
    NONE = "none"
    HIGHSCHOOL = "highschool"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    PHD = "phd"
    EQUIVALENT_EXPERIENCE = "equivalent_experience"


# ---------------------------------------------------------------------------
# Shared with the AI service (must match SCHEMA_CONTRACT.md)
# ---------------------------------------------------------------------------

class ExtractionResult(BaseModel):
    skills: dict[str, int] = Field(default_factory=dict)
    certifications: list[str] = Field(default_factory=list)
    education_level: EducationLevel = EducationLevel.NONE
    raw_summary: str | None = None


class JobRequirements(BaseModel):
    required_skills: dict[str, int] = Field(default_factory=dict)
    required_certifications: list[str] = Field(default_factory=list)
    min_education_level: EducationLevel | None = None


# ---------------------------------------------------------------------------
# Candidate side
# ---------------------------------------------------------------------------

class DisclosureLevel(str, Enum):
    """
    The three progressive-disclosure stages. A candidate starts ANONYMOUS
    and only moves forward when they choose to.
    """

    ANONYMOUS = "anonymous"
    VERIFIED_CANDIDATE = "verified_candidate"
    FULL_DISCLOSURE = "full_disclosure"


class CVSubmission(BaseModel):
    """What a client sends us to register a new candidate from raw CV text."""

    cv_text: str = Field(..., min_length=1)
    # Real name/email/phone are collected but kept private server-side until
    # the candidate explicitly discloses them (see DisclosureLevel).
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class CandidateProfile(BaseModel):
    """
    Internal, private record of a candidate. Never returned wholesale over
    the API - route handlers pick out only the fields allowed at the
    candidate's current disclosure level.
    """

    candidate_id: str
    anonymized_ref: str  # e.g. "PX-104" - this is what employers see pre-disclosure
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    extraction: ExtractionResult
    cv_source: str = "text"  # "text" or "pdf"
    extracted_text: str | None = None  # raw text read from an uploaded PDF, if any
    disclosure_level: DisclosureLevel = DisclosureLevel.ANONYMOUS


# ---------------------------------------------------------------------------
# Employer / job side
# ---------------------------------------------------------------------------

class EmployerVerificationResult(BaseModel):
    company_name: str
    domain: str
    company_identity_verified: bool
    domain_ownership_verified: bool
    job_posting_authorized: bool
    recruiter_authorized: bool

    @property
    def overall_verified(self) -> bool:
        return all(
            [
                self.company_identity_verified,
                self.domain_ownership_verified,
                self.job_posting_authorized,
                self.recruiter_authorized,
            ]
        )


class JobCreateRequest(BaseModel):
    """What an employer client sends us to post a new job."""

    title: str
    company_name: str
    domain: str
    salary: str | None = None
    description: str = Field(..., min_length=1, description="Free-text job description; AI #2 parses this.")


class JobPosting(BaseModel):
    job_id: str
    title: str
    company_name: str
    domain: str
    salary: str | None = None
    description: str
    requirements: JobRequirements
    verification: EmployerVerificationResult
    is_active: bool = True


# ---------------------------------------------------------------------------
# Matching (rules engine output) and Midnight proof
# ---------------------------------------------------------------------------

class CriterionResult(BaseModel):
    criterion: str
    required: str
    satisfied: bool


class MatchTier(str, Enum):
    """The graded output an employer sees, instead of (or alongside) a bare pass/fail."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class MatchResult(BaseModel):
    candidate_ref: str
    job_id: str
    criteria: list[CriterionResult]
    score: float = Field(ge=0.0, le=1.0, description="Fraction of criteria satisfied, 0.0-1.0.")
    tier: MatchTier
    overall_match: bool


class ProofResult(BaseModel):
    """
    Shaped so that whether this came from a real Midnight ZK proof
    (midnight_client.py calling midnight_service/) or the offline mock
    (midnight_mock.py), nothing downstream needs to know the difference.
    """

    proof_id: str
    verified: bool
    claim: str
    claim_hash: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ApplicationResult(BaseModel):
    """What an employer is allowed to see after a candidate applies: no PII, just proof."""

    candidate_ref: str
    job_id: str
    match: MatchResult
    proof: ProofResult
    disclosure_level: DisclosureLevel
    # Populated only once disclosure_level reaches FULL_DISCLOSURE:
    contact: dict[str, str] | None = None
