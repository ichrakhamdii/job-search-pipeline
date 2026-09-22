import os
import json
import time
from typing import List

import requests
from pydantic import BaseModel

API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
BATCH_SIZE = 15
DESCRIPTION_CHAR_LIMIT = 1500
MAX_RETRIES = 3


class JobVerdict(BaseModel):
    job_index: int
    recommendation: str  # "strong_match" | "possible_match" | "not_a_fit"
    rationale: str
    seniority_fit: str  # "matches" | "overqualified" | "underqualified" | "unclear"
    visa_claim_credible: bool
    confidence: str  # "low" | "medium" | "high"


class JudgeResponse(BaseModel):
    verdicts: List[JobVerdict]


def is_configured() -> bool:
    return bool(API_KEY)


def _build_profile_brief(profile: dict) -> str:
    lines = [
        f"Candidate: {profile.get('name')}",
        f"Summary: {profile.get('summary')}",
        f"Years of experience: {profile.get('years_experience')}",
        f"Target titles: {', '.join(profile.get('target_titles', []))}",
        f"Key skills: {', '.join(profile.get('skills', []))}",
        "Experience:",
    ]
    for exp in profile.get("experience", []):
        lines.append(f"  - {exp.get('title')} at {exp.get('company')} ({exp.get('dates')}): {exp.get('description')}")
    lines.append("Projects:")
    for p in profile.get("projects", []):
        lines.append(f"  - {p.get('title')} ({p.get('technologies')}): {p.get('description')}")
    lines.append("Certifications: " + ", ".join(profile.get("certifications", [])))
    lines.append("Education: " + ", ".join(profile.get("education", [])))
    lines.append(f"Location: {profile.get('location')}; open to remote: {profile.get('open_to_remote')}")
    return "\n".join(lines)


SYSTEM_TEMPLATE = """You are an expert technical recruiter evaluating job postings against a specific \
candidate's profile. Judge fit rigorously based on actual skills/experience/education overlap - do not \
be swayed by keyword stuffing in the posting. Also assess whether any visa sponsorship or \
international-candidate claim in the posting looks genuine and specific, versus generic boilerplate \
("all backgrounds welcome" type language with no real sponsorship commitment).

Candidate profile:
{profile_brief}

Respond with ONLY a single JSON object (no markdown, no commentary) of this exact shape:
{{
  "verdicts": [
    {{
      "job_index": <integer, matches the bracketed [N] index of the job>,
      "recommendation": "strong_match" | "possible_match" | "not_a_fit",
      "rationale": "<one concise sentence explaining the verdict>",
      "seniority_fit": "matches" | "overqualified" | "underqualified" | "unclear",
      "visa_claim_credible": true | false,
      "confidence": "low" | "medium" | "high"
    }}
  ]
}}
Include exactly one verdict per job listed below, in any order, using the correct job_index.
"""


def _call_groq(system_prompt: str, user_prompt: str) -> dict:
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    for attempt in range(MAX_RETRIES):
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 429 and attempt < MAX_RETRIES - 1:
            wait = float(resp.headers.get("retry-after", 5 * (attempt + 1)))
            print(f"[judge] Rate limited, retrying in {wait:.0f}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Groq API: exhausted retries")


def judge_jobs(profile: dict, jobs: list[dict], batch_size: int = BATCH_SIZE) -> dict:
    """Run already-shortlisted jobs through a free open-source LLM (via Groq) for deeper
    reasoning about fit.

    Returns {job_index: verdict_dict}, where job_index matches the position of the job in
    the input `jobs` list. Only call this on a pre-filtered shortlist (e.g. stage-1 >=60%
    matches) - an LLM pass over every raw scraped job would be far slower for little extra
    signal over the embedding stage.
    """
    if not is_configured():
        print("[judge] Skipped: set GROQ_API_KEY to enable the LLM judge stage.")
        return {}
    if not jobs:
        return {}

    profile_brief = _build_profile_brief(profile)
    system_prompt = SYSTEM_TEMPLATE.format(profile_brief=profile_brief)

    results: dict[int, dict] = {}
    for start in range(0, len(jobs), batch_size):
        batch = jobs[start:start + batch_size]
        listing_lines = []
        for i, job in enumerate(batch):
            desc = (job.get("description") or "")[:DESCRIPTION_CHAR_LIMIT]
            listing_lines.append(
                f"[{i}] Title: {job.get('title')}\nCompany: {job.get('company')}\n"
                f"Location: {job.get('location')}\nDescription: {desc}\n"
            )
        user_prompt = (
            "Evaluate each of the following jobs for this candidate. "
            "Return exactly one verdict per job, using its bracketed number as job_index.\n\n"
            + "\n".join(listing_lines)
        )

        try:
            raw = _call_groq(system_prompt, user_prompt)
            content = raw["choices"][0]["message"]["content"]
            parsed = JudgeResponse.model_validate(json.loads(content))
            for verdict in parsed.verdicts:
                results[start + verdict.job_index] = verdict.model_dump()
        except Exception as e:
            print(f"[judge] ERROR on batch starting at index {start}: {e}")

    return results
