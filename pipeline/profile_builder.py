"""Structure raw CV text into the candidate-profile shape via LLM extraction.

Shared logic used by both the CLI (build_profile.py) and the FastAPI backend
(app/services/profile_service.py) - same groq_client.py pattern as judge.py.
"""
import json
from typing import List

from pydantic import BaseModel

from . import groq_client


class Experience(BaseModel):
    title: str
    company: str
    dates: str
    description: str


class Project(BaseModel):
    title: str
    dates: str
    technologies: str
    description: str


class ExtractedProfile(BaseModel):
    name: str
    email: str
    location: str
    open_to_remote: bool
    years_experience: float
    target_titles: List[str]
    summary: str
    skills: List[str]
    experience: List[Experience]
    projects: List[Project]
    education: List[str]
    certifications: List[str]
    languages: List[str]


SYSTEM_PROMPT = """You extract structured candidate profile data from resume/CV text for a job-matching \
pipeline. The CV may be in any language (English, French, Arabic, etc.) - translate all free-text \
fields (summary, experience descriptions, project descriptions) into English, since the pipeline \
matches against English-language job postings. Keep proper nouns (people, companies, schools) as \
written in the original, transliterating if needed.

Rules:
- "skills" must be a flat list of individual technologies/tools/methods (e.g. "Python", "Docker"), \
never full sentences.
- "target_titles" should be 3-7 realistic job titles this candidate should search for, inferred from \
their actual experience and skills, even if the CV does not state a target role explicitly.
- "years_experience" is a numeric estimate (can be a decimal) of total professional experience, \
based on the work history's date ranges. Count internships as experience.
- "open_to_remote" should be true unless the CV explicitly states an on-site-only preference.
- If a field genuinely has no information in the CV, use an empty string or empty list - do not \
invent facts.

Respond with ONLY a single JSON object matching this exact shape:
{
  "name": "...",
  "email": "...",
  "location": "...",
  "open_to_remote": true,
  "years_experience": 0,
  "target_titles": ["...", "..."],
  "summary": "...",
  "skills": ["...", "..."],
  "experience": [{"title": "...", "company": "...", "dates": "...", "description": "..."}],
  "projects": [{"title": "...", "dates": "...", "technologies": "...", "description": "..."}],
  "education": ["..."],
  "certifications": ["..."],
  "languages": ["..."]
}
"""


def build_profile_from_cv(cv_text: str, api_key: str | None = None) -> dict:
    """api_key: pass explicitly in any multi-user context. Falls back to GROQ_API_KEY from
    the environment for single-user CLI use.
    """
    if not groq_client.is_configured(api_key):
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com and add it to .env."
        )
    raw = groq_client.call_groq(SYSTEM_PROMPT, cv_text, api_key=api_key, temperature=0.1,
                                 log_prefix="profile_builder")
    content = raw["choices"][0]["message"]["content"]
    parsed = ExtractedProfile.model_validate(json.loads(content))
    return parsed.model_dump()
