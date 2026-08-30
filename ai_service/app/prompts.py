"""
What this file does
--------------------
Holds the actual text of the prompts sent to Claude, kept separate from the
calling code in extraction.py so they're easy to tune during the hackathon
without hunting through request-building logic. Both prompts ask Claude to
act purely as an extractor - turning messy natural-language text into the
exact JSON shape defined in models.py - and nothing more. This matches the
pitch doc's principle "AI = extraction, not the trust decision": the model
never judges whether someone is "qualified", it only pulls out facts.
"""

CV_EXTRACTION_SYSTEM_PROMPT = """You are a resume/CV data extraction engine.

You will be given the raw text of a candidate's CV. Extract ONLY factual,
explicitly-stated or clearly-implied information. Do not guess wildly, do
not invent skills that aren't mentioned, and do not evaluate whether the
candidate is "good" - you are extracting facts, not making a hiring
judgment.

Return your answer using the `record_extraction` tool exactly once. Fields:

- skills: an object mapping lowercase skill names to years of experience as
  integers (e.g. {"python": 4, "postgresql": 2}). If a skill is mentioned
  but a duration isn't clear, use 0.
- certifications: a list of lowercase certification identifiers
  (e.g. ["aws_certified", "pmp_certified"]).
- education_level: one of "none", "highschool", "bachelors", "masters",
  "phd", "equivalent_experience" - pick the highest level clearly evidenced.
- raw_summary: one or two plain sentences summarizing the candidate's
  background, for internal display only.
"""

JOB_REQUIREMENTS_SYSTEM_PROMPT = """You are a job-description parsing engine.

You will be given a free-text job description written by an employer.
Extract the concrete, checkable requirements a candidate would need to meet.
Do not add requirements the text doesn't support.

Return your answer using the `record_requirements` tool exactly once. Fields:

- required_skills: an object mapping lowercase skill names to the minimum
  years of experience required as integers. If no specific duration is
  given but the skill is required, use 0.
- required_certifications: a list of lowercase certification identifiers.
- min_education_level: one of "none", "highschool", "bachelors", "masters",
  "phd", "equivalent_experience", or null if the posting doesn't require a
  specific education level.
"""

# JSON-schema "tool" definitions used to force Claude to answer in exactly
# the shape our Pydantic models expect (Anthropic tool-use / structured
# output). Using a tool call instead of asking for "JSON in your reply" is
# more reliable - Claude can't wrap it in markdown fences or add commentary.

EXTRACTION_TOOL = {
    "name": "record_extraction",
    "description": "Record structured candidate credentials extracted from a CV.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skills": {
                "type": "object",
                "additionalProperties": {"type": "integer"},
            },
            "certifications": {
                "type": "array",
                "items": {"type": "string"},
            },
            "education_level": {
                "type": "string",
                "enum": ["none", "highschool", "bachelors", "masters", "phd", "equivalent_experience"],
            },
            "raw_summary": {"type": "string"},
        },
        "required": ["skills", "certifications", "education_level"],
    },
}

REQUIREMENTS_TOOL = {
    "name": "record_requirements",
    "description": "Record structured job requirements extracted from a job description.",
    "input_schema": {
        "type": "object",
        "properties": {
            "required_skills": {
                "type": "object",
                "additionalProperties": {"type": "integer"},
            },
            "required_certifications": {
                "type": "array",
                "items": {"type": "string"},
            },
            "min_education_level": {
                "type": ["string", "null"],
                "enum": ["none", "highschool", "bachelors", "masters", "phd", "equivalent_experience", None],
            },
        },
        "required": ["required_skills", "required_certifications"],
    },
}
