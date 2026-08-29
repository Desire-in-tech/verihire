"""
What this file does
--------------------
This is the "explicit rules" box from the pitch doc's architecture diagram:

    AI extracts credentials  -->  RULES ENGINE (this file)  -->  Midnight verifies

The AI never decides whether a candidate is qualified. This file does, and
it does it with plain deterministic comparisons - every decision it makes
can be printed out as a human-readable reason (see CriterionResult), which
is exactly what should be turned into a cryptographic claim for Midnight to
verify. There is no AI call anywhere in this file on purpose.
"""

from .models import CriterionResult, ExtractionResult, JobRequirements, MatchResult, MatchTier


def _tier_for_score(score: float, all_satisfied: bool) -> MatchTier:
    """
    Maps a 0.0-1.0 fraction of satisfied criteria to the graded label an
    employer actually sees ("excellent" / "good" / "average" / "poor")
    instead of a bare pass/fail. These cutoffs are a hackathon-simple
    starting point, not a scientifically tuned scoring model - easy to
    retune in one place once you have real seed data to calibrate against.
    """
    if all_satisfied:
        return MatchTier.EXCELLENT
    if score >= 0.75:
        return MatchTier.GOOD
    if score >= 0.5:
        return MatchTier.AVERAGE
    return MatchTier.POOR


def evaluate(candidate_ref: str, job_id: str, extraction: ExtractionResult, requirements: JobRequirements) -> MatchResult:
    criteria: list[CriterionResult] = []

    for skill, min_years in requirements.required_skills.items():
        candidate_years = extraction.skills.get(skill, None)
        satisfied = candidate_years is not None and candidate_years >= min_years
        required_desc = f">= {min_years} years" if min_years > 0 else "present"
        criteria.append(CriterionResult(criterion=skill, required=required_desc, satisfied=satisfied))

    for cert in requirements.required_certifications:
        satisfied = cert in extraction.certifications
        criteria.append(CriterionResult(criterion=cert, required="present", satisfied=satisfied))

    if requirements.min_education_level is not None:
        satisfied = _education_meets_minimum(extraction.education_level, requirements.min_education_level)
        criteria.append(
            CriterionResult(
                criterion="education",
                required=f"{requirements.min_education_level.value} or higher (or equivalent experience)",
                satisfied=satisfied,
            )
        )

    overall_match = all(c.satisfied for c in criteria) if criteria else False
    score = (sum(1 for c in criteria if c.satisfied) / len(criteria)) if criteria else 0.0
    tier = _tier_for_score(score, overall_match)

    return MatchResult(
        candidate_ref=candidate_ref,
        job_id=job_id,
        criteria=criteria,
        score=round(score, 2),
        tier=tier,
        overall_match=overall_match,
    )


# Ordering used to compare education levels. "equivalent_experience" is
# treated as satisfying any requirement, matching the "Bachelor's degree OR
# equivalent experience" language from the pitch doc.
_EDUCATION_RANK = {
    "none": 0,
    "highschool": 1,
    "bachelors": 2,
    "masters": 3,
    "phd": 4,
}


def _education_meets_minimum(candidate_level, required_level) -> bool:
    if candidate_level.value == "equivalent_experience":
        return True
    return _EDUCATION_RANK.get(candidate_level.value, 0) >= _EDUCATION_RANK.get(required_level.value, 0)
