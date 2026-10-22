from Backend.models import JobCriteria, ExtractedCVData, RulesEngineResult


class RulesEngine:
    """
    Deterministic rules engine for evaluating a CV against job criteria.

    AI extracts facts.
    This engine makes the actual matching decision.

    Skills are represented as:

        required_skills = {
            "python": 3,
            "fastapi": 2
        }

        candidate_skills = {
            "python": 4,
            "fastapi": 1
        }

    A required skill with 0 years means the candidate only needs to
    demonstrate that the skill is present.
    """

    @staticmethod
    def evaluate(
        job_id: str,
        job_criteria: JobCriteria,
        cv_data: ExtractedCVData,
    ) -> RulesEngineResult:

        missing_requirements: list[str] = []
        matched_requirements: list[str] = []

        # ---------------------------------------------------------------
        # 1. Required skills + skill-specific experience
        # ---------------------------------------------------------------

        candidate_skills = {
            skill.strip().lower(): max(0, int(years))
            for skill, years in cv_data.skills.items()
            if isinstance(skill, str)
        }

        skills_match = True

        for required_skill, required_years in job_criteria.required_skills.items():
            normalized_skill = required_skill.strip().lower()
            required_years = max(0, int(required_years))

            candidate_years = candidate_skills.get(normalized_skill)

            if candidate_years is None:
                skills_match = False
                missing_requirements.append(
                    f"Missing required skill: {required_skill}"
                )
                continue

            if required_years == 0:
                matched_requirements.append(
                    f"Has required skill: {required_skill}"
                )
                continue

            if candidate_years >= required_years:
                matched_requirements.append(
                    f"Has {required_skill} experience: "
                    f"{candidate_years} years "
                    f"(required: {required_years})"
                )
            else:
                skills_match = False
                missing_requirements.append(
                    f"Insufficient {required_skill} experience: "
                    f"{candidate_years} years "
                    f"(required: {required_years})"
                )

        # ---------------------------------------------------------------
        # 2. Overall years of experience
        # ---------------------------------------------------------------
        #
        # ExtractedCVData currently does not contain a separate
        # years_experience field. The best deterministic approximation
        # is the highest skill experience extracted from the CV.
        #
        # This keeps the current backend contract consistent while the
        # AI service remains responsible for extracting skill durations.
        # ---------------------------------------------------------------

        candidate_years_experience = (
            max(candidate_skills.values())
            if candidate_skills
            else 0
        )

        years_match = (
            candidate_years_experience
            >= job_criteria.min_years_experience
        )

        if years_match:
            matched_requirements.append(
                f"Has {candidate_years_experience} years experience "
                f"(required: {job_criteria.min_years_experience})"
            )
        else:
            missing_requirements.append(
                f"Only has {candidate_years_experience} years experience "
                f"(required: {job_criteria.min_years_experience})"
            )

        # ---------------------------------------------------------------
        # 3. Education
        # ---------------------------------------------------------------

        education_match = True

        if job_criteria.education_level:
            required_education = (
                job_criteria.education_level.strip().lower()
            )

            candidate_education = (
                (cv_data.education_level or "none")
                .strip()
                .lower()
            )

            education_match = RulesEngine._education_matches(
                required_education,
                candidate_education,
            )

            if education_match:
                matched_requirements.append(
                    f"Education requirement met: "
                    f"{cv_data.education_level}"
                )
            else:
                missing_requirements.append(
                    f"Education requirement not met: "
                    f"requires {job_criteria.education_level}, "
                    f"candidate has {cv_data.education_level or 'none'}"
                )

        # ---------------------------------------------------------------
        # 4. Certifications
        # ---------------------------------------------------------------

        candidate_certifications = {
            cert.strip().lower()
            for cert in cv_data.certifications
            if isinstance(cert, str)
        }

        certifications_match = True

        for required_cert in job_criteria.certifications:
            normalized_cert = required_cert.strip().lower()

            if normalized_cert in candidate_certifications:
                matched_requirements.append(
                    f"Has required certification: {required_cert}"
                )
            else:
                certifications_match = False
                missing_requirements.append(
                    f"Missing certification: {required_cert}"
                )

        # ---------------------------------------------------------------
        # 5. Languages
        # ---------------------------------------------------------------
        #
        candidate_languages = {
            language.strip().lower()
            for language in cv_data.languages
            if isinstance(language, str) and language.strip()
        }
        required_languages = {
            language.strip().lower()
            for language in job_criteria.languages
            if isinstance(language, str) and language.strip()
        }
        languages_match = required_languages.issubset(candidate_languages)

        for language in required_languages:
            if language in candidate_languages:
                matched_requirements.append(f"Speaks required language: {language}")
            else:
                missing_requirements.append(f"Missing required language: {language}")

        # ---------------------------------------------------------------
        # 6. Calculate score
        # ---------------------------------------------------------------

        total_criteria = (
            len(job_criteria.required_skills)
            + 1  # overall experience
            + (1 if job_criteria.education_level else 0)
            + len(job_criteria.languages)
            + len(job_criteria.certifications)
        )

        met_criteria = len(matched_requirements)

        if total_criteria == 0:
            score = 100.0
        else:
            score = (met_criteria / total_criteria) * 100

        score = round(score, 2)

        # ---------------------------------------------------------------
        # 7. Final deterministic match decision
        # ---------------------------------------------------------------

        matches = (
            skills_match
            and years_match
            and education_match
            and languages_match
            and certifications_match
        )

        reasoning = RulesEngine._generate_reasoning(
            matched_requirements,
            missing_requirements,
            score,
            matches,
        )

        return RulesEngineResult(
            job_id=job_id,
            matches=matches,
            score=score,
            missing_requirements=missing_requirements,
            matched_requirements=matched_requirements,
            reasoning=reasoning,
        )

    @staticmethod
    def _education_matches(
        required: str,
        candidate: str,
    ) -> bool:
        """
        Determine whether the candidate's education satisfies the
        job's minimum education requirement.

        Education hierarchy:

            none < highschool < bachelors < masters < phd

        equivalent_experience is accepted as an alternative when the
        job explicitly allows equivalent experience.
        """

        if required in {"none", ""}:
            return True

        if required == "equivalent_experience":
            return candidate == "equivalent_experience"

        if candidate == "equivalent_experience":
            return False

        education_rank = {
            "none": 0,
            "highschool": 1,
            "bachelors": 2,
            "masters": 3,
            "phd": 4,
        }

        required_rank = education_rank.get(required)
        candidate_rank = education_rank.get(candidate)

        if required_rank is None or candidate_rank is None:
            return False

        return candidate_rank >= required_rank

    @staticmethod
    def _generate_reasoning(
        matched: list[str],
        missing: list[str],
        score: float,
        matches: bool,
    ) -> str:
        """Generate human-readable reasoning for the match decision."""

        if matches:
            if score >= 90:
                return (
                    f"Excellent match ({score}% match rate). "
                    "Candidate satisfies all required criteria."
                )

            if score >= 75:
                return (
                    f"Good match ({score}% match rate). "
                    "Candidate satisfies all mandatory criteria."
                )

            return (
                f"Qualified match ({score}% match rate). "
                "Candidate satisfies all mandatory criteria."
            )

        if score >= 75:
            return (
                f"Strong partial match ({score}% match rate). "
                f"Missing: {', '.join(missing[:3])}."
            )

        if score >= 60:
            return (
                f"Partial match ({score}% match rate). "
                f"Missing: {', '.join(missing[:3])}."
            )

        return (
            f"Poor match ({score}% match rate). "
            f"Critical requirements missing: {', '.join(missing[:3])}."
        )
