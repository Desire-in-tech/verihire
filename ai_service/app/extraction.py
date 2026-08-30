"""
What this file does
--------------------
This is the actual "AI #1" and "AI #2" logic from the pitch doc: it takes
raw CV text or a raw job description and turns it into the structured
Pydantic objects defined in models.py.

Each function tries a real Claude call first (via the Anthropic tool-use
API, which forces the model to answer in our exact JSON shape). If no
`ANTHROPIC_API_KEY` is configured (settings.has_ai is False) or the API
call fails for any reason, it falls back to a small offline, keyword-based
extractor instead. That fallback exists purely so the whole demo can still
be run and rehearsed without an API key or with no internet - it is not
meant to be "smart", just good enough to not block the rest of the team.
"""

import re

import anthropic

from .config import settings
from .models import ExtractionResult, JobRequirements, EducationLevel
from .prompts import (
    CV_EXTRACTION_SYSTEM_PROMPT,
    JOB_REQUIREMENTS_SYSTEM_PROMPT,
    EXTRACTION_TOOL,
    REQUIREMENTS_TOOL,
)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _call_claude_tool(system_prompt: str, user_text: str, tool: dict) -> dict:
    """
    Sends one message to Claude, forcing it to respond by calling `tool`.
    Returns the tool call's raw input dict (still unvalidated JSON at this
    point - the caller wraps it in a Pydantic model, which is where actual
    validation happens).
    """
    client = _get_client()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_text}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == tool["name"]:
            return block.input
    raise RuntimeError("Claude did not return the expected tool call.")


# ---------------------------------------------------------------------------
# Offline fallback extractors (no API key needed)
# ---------------------------------------------------------------------------

# A small, hackathon-sized list of skills we know how to spot by keyword.
# Extend this list freely - it only feeds the offline fallback path.
_KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "go", "rust",
    "postgresql", "mysql", "mongodb", "redis",
    "aws", "gcp", "azure", "docker", "kubernetes",
    "backend", "frontend", "fastapi", "django", "flask", "react",
]

_CERT_PATTERNS = {
    "aws_certified": r"aws certifi",
    "pmp_certified": r"pmp certifi",
    "azure_certified": r"azure certifi",
}


def _skills_with_years(text: str) -> dict[str, int]:
    """
    Finds known skills and, when possible, a "N years" figure mentioned in
    the same sentence (e.g. "4 years of experience building Python
    services" - the number and the skill aren't adjacent, but they're in
    the same sentence). Defaults to 0 ("present, duration unclear") when no
    number is found nearby. This is only used by the offline fallback path;
    a real Claude call reads this the way a person would instead.
    """
    skills: dict[str, int] = {}
    sentences = re.split(r"(?<=[.\n])", text)
    for sentence in sentences:
        year_numbers = [int(n) for n in re.findall(r"(\d+)\+?\s*years?", sentence)]
        best_year = max(year_numbers) if year_numbers else 0
        for skill in _KNOWN_SKILLS:
            if skill in sentence:
                skills[skill] = max(skills.get(skill, 0), best_year)
    return skills


def _fallback_extract_cv(cv_text: str) -> ExtractionResult:
    text = cv_text.lower()

    skills = _skills_with_years(text)

    certifications = [cert for cert, pattern in _CERT_PATTERNS.items() if re.search(pattern, text)]

    if "phd" in text or "doctorate" in text:
        education = EducationLevel.PHD
    elif "master" in text:
        education = EducationLevel.MASTERS
    elif "bachelor" in text or "b.sc" in text or "bsc" in text:
        education = EducationLevel.BACHELORS
    elif "equivalent experience" in text:
        education = EducationLevel.EQUIVALENT_EXPERIENCE
    else:
        education = EducationLevel.NONE

    return ExtractionResult(
        skills=skills,
        certifications=certifications,
        education_level=education,
        raw_summary="(offline fallback extraction - no ANTHROPIC_API_KEY configured)",
    )


def _fallback_extract_job(description: str) -> JobRequirements:
    text = description.lower()

    required_skills = _skills_with_years(text)

    required_certifications = [cert for cert, pattern in _CERT_PATTERNS.items() if re.search(pattern, text)]

    if "bachelor" in text:
        min_education = EducationLevel.BACHELORS
    elif "master" in text:
        min_education = EducationLevel.MASTERS
    elif "equivalent experience" in text:
        min_education = EducationLevel.EQUIVALENT_EXPERIENCE
    else:
        min_education = None

    return JobRequirements(
        required_skills=required_skills,
        required_certifications=required_certifications,
        min_education_level=min_education,
    )


# ---------------------------------------------------------------------------
# Public functions - these are what main.py calls
# ---------------------------------------------------------------------------

def extract_cv(cv_text: str) -> ExtractionResult:
    """AI #1: turn raw CV text into structured candidate credentials."""
    if not settings.has_ai:
        return _fallback_extract_cv(cv_text)
    try:
        raw = _call_claude_tool(CV_EXTRACTION_SYSTEM_PROMPT, cv_text, EXTRACTION_TOOL)
        return ExtractionResult.model_validate(raw)
    except Exception:
        # Never let a flaky API call take down the demo - fall back quietly.
        return _fallback_extract_cv(cv_text)


def extract_job_requirements(description: str) -> JobRequirements:
    """AI #2: turn a free-text job description into structured requirements."""
    if not settings.has_ai:
        return _fallback_extract_job(description)
    try:
        raw = _call_claude_tool(JOB_REQUIREMENTS_SYSTEM_PROMPT, description, REQUIREMENTS_TOOL)
        return JobRequirements.model_validate(raw)
    except Exception:
        return _fallback_extract_job(description)
