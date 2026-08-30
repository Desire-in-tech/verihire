from models import JobCriteria, ExtractedCVData, RulesEngineResult

class RulesEngine:
    """
    Rules engine that evaluates if a CV matches job criteria.
    Compares extracted CV data against job requirements and returns pass/fail decision.
    """
    
    @staticmethod
    def evaluate(job_id: str, job_criteria: JobCriteria, cv_data: ExtractedCVData) -> RulesEngineResult:
        """
        Evaluate if CV data matches job criteria.
        
        Args:
            job_id: The job being evaluated against
            job_criteria: The job's requirements
            cv_data: The extracted CV data
            
        Returns:
            RulesEngineResult with match status and detailed feedback
        """
        missing_requirements = []
        matched_requirements = []
        
        # Check required skills
        cv_skills_lower = [skill.lower() for skill in cv_data.skills]
        for required_skill in job_criteria.required_skills:
            if required_skill.lower() in cv_skills_lower:
                matched_requirements.append(f"Has required skill: {required_skill}")
            else:
                missing_requirements.append(f"Missing required skill: {required_skill}")
        
        # Check years of experience
        years_match = cv_data.years_experience >= job_criteria.min_years_experience
        if years_match:
            matched_requirements.append(
                f"Has {cv_data.years_experience} years experience (required: {job_criteria.min_years_experience})"
            )
        else:
            missing_requirements.append(
                f"Only has {cv_data.years_experience} years experience (required: {job_criteria.min_years_experience})"
            )
        
        # Check education level (soft requirement)
        education_match = True
        if job_criteria.education_level:
            # Check if education requirement is mentioned or acceptable
            if cv_data.education_level:
                if "Master's" in job_criteria.education_level and "Master's" in cv_data.education_level:
                    matched_requirements.append(f"Has {cv_data.education_level}")
                elif "Bachelor's" in job_criteria.education_level and ("Bachelor's" in cv_data.education_level or "Master's" in cv_data.education_level):
                    matched_requirements.append(f"Has {cv_data.education_level}")
                elif "Self-taught" in job_criteria.education_level:
                    matched_requirements.append("Education requirement flexible")
                else:
                    education_match = False
                    missing_requirements.append(f"Education mismatch: has {cv_data.education_level}")
            else:
                education_match = False
        
        # Check languages
        cv_languages_lower = [lang.lower() for lang in cv_data.languages]
        languages_match = True
        for required_language in job_criteria.languages:
            if required_language.lower() in cv_languages_lower:
                matched_requirements.append(f"Speaks required language: {required_language}")
            else:
                languages_match = False
                missing_requirements.append(f"Missing language: {required_language}")
        
        # Check certifications
        cv_certs_lower = [cert.lower() for cert in cv_data.certifications]
        for required_cert in job_criteria.certifications:
            if required_cert.lower() in cv_certs_lower:
                matched_requirements.append(f"Has required certification: {required_cert}")
            else:
                missing_requirements.append(f"Missing certification: {required_cert}")
        
        # Calculate score (0-100)
        total_criteria = (
            len(job_criteria.required_skills) +
            1 +  # years of experience
            (1 if job_criteria.education_level else 0) +
            len(job_criteria.languages) +
            len(job_criteria.certifications)
        )
        
        if total_criteria == 0:
            score = 100.0
        else:
            met_criteria = len(matched_requirements)
            score = (met_criteria / total_criteria) * 100
        
        # Determine if CV matches (must meet all required skills and years of experience)
        matched_skill_count = len([m for m in matched_requirements if "Has required skill:" in m])
        matches = (matched_skill_count == len(job_criteria.required_skills)) and years_match
        
        reasoning = RulesEngine._generate_reasoning(matched_requirements, missing_requirements, score)
        
        return RulesEngineResult(
            job_id=job_id,
            matches=matches,
            score=round(score, 2),
            missing_requirements=missing_requirements,
            matched_requirements=matched_requirements,
            reasoning=reasoning
        )
    
    @staticmethod
    def _generate_reasoning(matched: list, missing: list, score: float) -> str:
        """Generate human-readable reasoning for the match decision."""
        if score >= 90:
            return f"Excellent match ({score}% match rate). Candidate meets nearly all requirements."
        elif score >= 75:
            return f"Good match ({score}% match rate). Candidate meets most key requirements."
        elif score >= 60:
            return f"Partial match ({score}% match rate). Candidate meets some requirements but is missing: {', '.join(missing[:2])}."
        else:
            return f"Poor match ({score}% match rate). Candidate is missing critical requirements: {', '.join(missing[:3])}."
