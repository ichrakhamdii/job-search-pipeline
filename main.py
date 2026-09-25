import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # must run before importing modules that read API keys at import time

import pandas as pd

from pipeline.pipeline_service import run_pipeline

ROOT = Path(__file__).parent
PROFILE_PATH = ROOT / "profile" / "candidate_profile.json"
OUTPUT_DIR = ROOT / "output"
SEEN_JOBS_PATH = OUTPUT_DIR / "seen_jobs.json"


def load_profile() -> dict:
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_seen() -> dict:
    if SEEN_JOBS_PATH.exists():
        with open(SEEN_JOBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(seen: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(SEEN_JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def env_api_keys() -> dict:
    """CLI single-user config: read everything from .env, once, at startup."""
    greenhouse = os.environ.get("GREENHOUSE_COMPANIES", "")
    lever = os.environ.get("LEVER_COMPANIES", "")
    return {
        "voyage_api_key": os.environ.get("VOYAGE_API_KEY") or None,
        "groq_api_key": os.environ.get("GROQ_API_KEY") or None,
        "adzuna_app_id": os.environ.get("ADZUNA_APP_ID") or None,
        "adzuna_app_key": os.environ.get("ADZUNA_APP_KEY") or None,
        "greenhouse_companies": [c.strip() for c in greenhouse.split(",") if c.strip()],
        "lever_companies": [c.strip() for c in lever.split(",") if c.strip()],
    }


def main():
    extra_query = sys.argv[1] if len(sys.argv) > 1 else None

    profile = load_profile()
    print(f"Loaded profile for {profile.get('name')}")

    titles = list(profile.get("target_titles", []))
    if extra_query:
        titles.append(extra_query)
    if not titles:
        titles = [""]
    print(f"Fetching jobs for target titles: {titles}")

    seen = load_seen()
    ranked = run_pipeline(profile, titles, seen, env_api_keys(), top_n=50, log=print)
    save_seen(seen)

    if not ranked:
        print("\nNothing to shortlist this run.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"shortlist_{timestamp}.csv"

    df = pd.DataFrame(ranked)
    cols = ["match_score", "llm_recommendation", "llm_confidence", "skills_score",
            "experience_score", "projects_score", "certifications_score", "education_score",
            "title", "company", "location", "source", "llm_rationale", "llm_seniority_fit",
            "international_signals", "visa_sponsorship", "llm_visa_claim_credible",
            "international_candidates", "remote_friendly", "matched_skills", "url", "posted_at"]
    df = df[[c for c in cols if c in df.columns]]
    df.to_csv(out_path, index=False)

    print(f"\nSaved ranked shortlist of NEW offers to {out_path}")
    print("\nTop 10 matches:")
    for row in ranked[:10]:
        flags = row["international_signals"] or "-"
        verdict = f" | LLM: {row['llm_recommendation']}" if row.get("llm_recommendation") else ""
        print(f"  {row['match_score']:5.1f}  {row['title']} @ {row['company']} ({row['source']}) [{flags}]{verdict}")


if __name__ == "__main__":
    main()
