"""Groq-powered generation: tailored CV summary, cover letter, and mock interview prep.

Same groq_client.py pattern as judge.py and build_profile.py - a shared module the FastAPI
backend imports directly, so this logic exists in exactly one place.
"""
import json

from . import groq_client

JOB_DESCRIPTION_CHAR_LIMIT = 4000


def _profile_brief(profile: dict) -> str:
    lines = [
        f"Name: {profile.get('name')}",
        f"Summary: {profile.get('summary')}",
        f"Years of experience: {profile.get('years_experience')}",
        f"Skills: {', '.join(profile.get('skills', []))}",
        "Experience:",
    ]
    for exp in profile.get("experience", []):
        lines.append(f"  - {exp.get('title')} at {exp.get('company')} ({exp.get('dates')}): {exp.get('description')}")
    lines.append("Projects:")
    for p in profile.get("projects", []):
        lines.append(f"  - {p.get('title')}: {p.get('description')}")
    lines.append("Education: " + ", ".join(profile.get("education", [])))
    lines.append("Certifications: " + ", ".join(profile.get("certifications", [])))
    return "\n".join(lines)


TAILOR_CV_SYSTEM = """You write concise, honest, tailored resume content. Given a candidate's real \
background and a specific job description, produce a tailored professional summary (2-3 sentences) \
and notes on which of the candidate's existing experience/project bullets to emphasize for this \
specific role, and why. Never invent skills or experience the candidate doesn't have - only \
reorder, emphasize, or rephrase what's genuinely there.

Candidate background:
{profile_brief}

Job description:
{job_description}

Respond with ONLY a JSON object of this shape:
{{"tailored_summary": "...", "emphasis_notes": "..."}}
"""

COVER_LETTER_SYSTEM = """You write grounded, specific cover letters - never generic filler. Given a \
candidate's real background and a job description, draft a cover letter (3-4 paragraphs) that \
references the candidate's actual, specific achievements and connects them directly to what the \
posting asks for. Do not invent facts.

Candidate background:
{profile_brief}

Job description:
{job_description}

Respond with ONLY a JSON object: {{"cover_letter": "..."}}
"""

MOCK_INTERVIEW_SYSTEM = """You prepare candidates for interviews. Given a candidate's real background \
and a job description, generate:
- 5 likely behavioral interview questions, each with a one-line note on what a strong answer covers
- 5 likely technical questions specific to the job's actual tech stack, each with a one-line note on \
what a strong answer covers
- one small technical exercise (a prompt only, not a solution) matching the job's real tech stack

Candidate background:
{profile_brief}

Job description:
{job_description}

Respond with ONLY a JSON object of this shape:
{{
  "behavioral_questions": [{{"question": "...", "what_a_good_answer_covers": "..."}}],
  "technical_questions": [{{"question": "...", "what_a_good_answer_covers": "..."}}],
  "technical_exercise": "..."
}}
"""


def tailor_cv(profile: dict, job_description: str, api_key: str | None = None) -> str:
    """Returns a first-draft tailored summary + emphasis notes as Markdown.
    Frame this as a starting point for the user to personalize further, never a final
    ready-to-send document - the same posture build_profile.py takes with extracted profiles.
    """
    system = TAILOR_CV_SYSTEM.format(
        profile_brief=_profile_brief(profile),
        job_description=job_description[:JOB_DESCRIPTION_CHAR_LIMIT],
    )
    raw = groq_client.call_groq(system, "Generate the tailored summary and emphasis notes now.",
                                 api_key=api_key, temperature=0.4, log_prefix="document_service")
    data = json.loads(raw["choices"][0]["message"]["content"])
    return (
        f"## Tailored Summary\n\n{data.get('tailored_summary', '')}\n\n"
        f"## What to Emphasize\n\n{data.get('emphasis_notes', '')}"
    )


def cover_letter(profile: dict, job_description: str, api_key: str | None = None) -> str:
    system = COVER_LETTER_SYSTEM.format(
        profile_brief=_profile_brief(profile),
        job_description=job_description[:JOB_DESCRIPTION_CHAR_LIMIT],
    )
    raw = groq_client.call_groq(system, "Generate the cover letter now.",
                                 api_key=api_key, temperature=0.5, log_prefix="document_service")
    data = json.loads(raw["choices"][0]["message"]["content"])
    return data.get("cover_letter", "")


def mock_interview(profile: dict, job_description: str, api_key: str | None = None) -> str:
    system = MOCK_INTERVIEW_SYSTEM.format(
        profile_brief=_profile_brief(profile),
        job_description=job_description[:JOB_DESCRIPTION_CHAR_LIMIT],
    )
    raw = groq_client.call_groq(system, "Generate the interview prep now.",
                                 api_key=api_key, temperature=0.4, log_prefix="document_service")
    data = json.loads(raw["choices"][0]["message"]["content"])

    lines = ["## Behavioral Questions\n"]
    for q in data.get("behavioral_questions", []):
        lines.append(f"- **{q.get('question')}**\n  _{q.get('what_a_good_answer_covers')}_\n")
    lines.append("## Technical Questions\n")
    for q in data.get("technical_questions", []):
        lines.append(f"- **{q.get('question')}**\n  _{q.get('what_a_good_answer_covers')}_\n")
    lines.append("## Technical Exercise\n")
    lines.append(data.get("technical_exercise", ""))
    return "\n".join(lines)
