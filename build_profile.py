import argparse
import json
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel

import groq_client
from cv_extractor import extract_text

ROOT = Path(__file__).parent
DEFAULT_OUTPUT = ROOT / "profile" / "candidate_profile.json"


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


def build_profile_from_cv(cv_text: str) -> dict:
    if not groq_client.is_configured():
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com and add it to .env."
        )
    raw = groq_client.call_groq(SYSTEM_PROMPT, cv_text, temperature=0.1, log_prefix="build_profile")
    content = raw["choices"][0]["message"]["content"]
    parsed = ExtractedProfile.model_validate(json.loads(content))
    return parsed.model_dump()


def main():
    parser = argparse.ArgumentParser(
        description="Build profile/candidate_profile.json automatically from a CV PDF."
    )
    parser.add_argument("cv_path", help="Path to the CV PDF file")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT),
                         help=f"Output path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    cv_path = Path(args.cv_path)
    if not cv_path.exists():
        print(f"File not found: {cv_path}", file=sys.stderr)
        sys.exit(1)
    if cv_path.suffix.lower() != ".pdf":
        print(f"Only PDF files are supported right now (got {cv_path.suffix}).", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    if output_path.exists():
        answer = input(f"{output_path} already exists. Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    print(f"Extracting text from {cv_path}...")
    cv_text = extract_text(str(cv_path))
    print(f"Extracted {len(cv_text)} characters. Sending to LLM for structuring...")

    profile = build_profile_from_cv(cv_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\nProfile saved to {output_path}")
    print(f"Name: {profile.get('name')}")
    print(f"Target titles: {', '.join(profile.get('target_titles', []))}")
    print(f"Skills ({len(profile.get('skills', []))}): {', '.join(profile.get('skills', [])[:10])}...")
    print("\nReview the generated file and adjust anything the extraction got wrong before running main.py.")


if __name__ == "__main__":
    main()
