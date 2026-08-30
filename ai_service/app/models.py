"""
What this file does
--------------------
Defines every data shape this service accepts and returns, using Pydantic.
FastAPI uses these classes to validate incoming requests and to build
outgoing JSON automatically. This is the "contract" side of the schema
described in SCHEMA_CONTRACT.md at the repo root - the backend team's
Pydantic models must match these field names and types exactly, since that
is the only thing keeping the two services in sync.
"""

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
# AI #1 - CV / credential extraction
# ---------------------------------------------------------------------------

class CVExtractionRequest(BaseModel):
    """What the backend sends us: the raw candidate CV as plain text."""

    cv_text: str = Field(..., min_length=1, description="Raw CV text pasted or parsed by the backend.")


class ExtractionResult(BaseModel):
    """
    What we send back to the backend: structured, private credentials.

    This never includes the candidate's name, contact info, or the raw CV
    text - only skills/experience/certifications/education. Keeping PII out
    of this model is what lets the backend pass it into the rules engine
    without accidentally leaking personal data further downstream.
    """

    skills: dict[str, int] = Field(
        default_factory=dict,
        description="skill name (lowercase) -> years of experience. 0 means 'present, duration unclear'.",
    )
    certifications: list[str] = Field(
        default_factory=list,
        description="lowercase certification identifiers, e.g. 'aws_certified'.",
    )
    education_level: EducationLevel = EducationLevel.NONE
    raw_summary: str | None = Field(
        default=None,
        description="Short internal-only summary of the candidate, for debugging/demo display.",
    )


# ---------------------------------------------------------------------------
# AI #2 - job requirement analysis
# ---------------------------------------------------------------------------

class JobDescriptionRequest(BaseModel):
    """What the backend sends us: an employer's free-text job description."""

    description: str = Field(..., min_length=1)


class JobRequirements(BaseModel):
    """What we send back: the job description turned into structured, checkable criteria."""

    required_skills: dict[str, int] = Field(
        default_factory=dict,
        description="skill name -> minimum years required. 0 means 'must simply be present'.",
    )
    required_certifications: list[str] = Field(default_factory=list)
    min_education_level: EducationLevel | None = None
