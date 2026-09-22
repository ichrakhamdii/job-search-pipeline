import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # must run before importing modules that read API keys at import time

import pandas as pd

from scrapers import remoteok, arbeitnow, weworkremotely, adzuna, greenhouse_lever, remotive, jobicy, himalayas
from matcher import rank_jobs, MIN_MATCH_SCORE
from judge import judge_jobs, is_configured as judge_configured

ROOT = Path(__file__).parent
PROFILE_PATH = ROOT / "profile" / "candidate_profile.json"
OUTPUT_DIR = ROOT / "output"
SEEN_JOBS_PATH = OUTPUT_DIR / "seen_jobs.json"

# Adzuna supports real server-side search ("what=" param), so it's worth querying once per
# target title to get genuinely targeted results. The others return their whole catalog
# regardless of query, so we fetch each once and filter locally against all target titles
# instead of re-hitting their APIs (and their rate limits) once per title.
TITLE_ITERATED_SOURCES = [adzuna]
FETCH_ONCE_SOURCES = [remoteok, arbeitnow, weworkremotely, greenhouse_lever, remotive, jobicy, himalayas]


def load_profile() -> dict:
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def job_fingerprint(job: dict) -> str:
    if job.get("url"):
        return job["url"].strip().lower()
    return f"{job.get('title','').strip().lower()}|{job.get('company','').strip().lower()}"


def load_seen() -> dict:
    if SEEN_JOBS_PATH.exists():
        with open(SEEN_JOBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(seen: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(SEEN_JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def filter_new_jobs(jobs: list[dict], seen: dict) -> list[dict]:
    """Only keep jobs never encountered in a previous run; record all current jobs as seen."""
    now = datetime.now(timezone.utc).isoformat()
    new_jobs = []
    for job in jobs:
        fp = job_fingerprint(job)
        if fp not in seen:
            new_jobs.append(job)
            seen[fp] = {"first_seen": now, "title": job.get("title"), "company": job.get("company")}
    return new_jobs


def job_matches_any_title(job: dict, titles: list[str]) -> bool:
    if not titles:
        return True
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    return any(t.lower() in text for t in titles)


def collect_jobs(titles: list[str]) -> list[dict]:
    all_jobs = []

    for source in TITLE_ITERATED_SOURCES:
        name = source.__name__.split(".")[-1]
        if hasattr(source, "is_configured") and not source.is_configured():
            print(f"[{name}] Skipped: not configured (missing API credentials).")
            continue
        for title in titles:
            try:
                jobs = source.fetch_jobs(query=title)
                print(f"[{name}] '{title}': fetched {len(jobs)} jobs")
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"[{name}] '{title}' ERROR: {e}", file=sys.stderr)

    for source in FETCH_ONCE_SOURCES:
        name = source.__name__.split(".")[-1]
        try:
            jobs = source.fetch_jobs(query="")
            matched = [j for j in jobs if job_matches_any_title(j, titles)]
            print(f"[{name}] fetched {len(jobs)} jobs, {len(matched)} matched target titles")
            all_jobs.extend(matched)
        except Exception as e:
            print(f"[{name}] ERROR: {e}", file=sys.stderr)

    return dedupe(all_jobs)


def dedupe(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for j in jobs:
        key = (j.get("title", "").strip().lower(), j.get("company", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)
    return unique


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

    jobs = collect_jobs(titles)
    print(f"Total unique jobs collected this run: {len(jobs)}")

    seen = load_seen()
    new_jobs = filter_new_jobs(jobs, seen)
    save_seen(seen)
    print(f"New jobs since last run: {len(new_jobs)}")

    if not new_jobs:
        print("\nNo new job offers since the last run. Nothing to shortlist.")
        return

    ranked = rank_jobs(profile, new_jobs, top_n=50)

    if not ranked:
        print(f"\nNo new offers reached the {MIN_MATCH_SCORE:.0f}% match threshold this run.")
        return

    if judge_configured():
        print(f"\nRunning LLM judge on {len(ranked)} shortlisted jobs...")
        verdicts = judge_jobs(profile, ranked)
        for idx, row in enumerate(ranked):
            v = verdicts.get(idx, {})
            row["llm_recommendation"] = v.get("recommendation", "")
            row["llm_rationale"] = v.get("rationale", "")
            row["llm_seniority_fit"] = v.get("seniority_fit", "")
            row["llm_visa_claim_credible"] = v.get("visa_claim_credible", "")
            row["llm_confidence"] = v.get("confidence", "")

        # The judge exists to catch false positives the embedding stage can't see
        # (e.g. a title that matches semantically but the actual role doesn't) - so a
        # clear "not_a_fit" verdict should actually drop the job, not just annotate it.
        before = len(ranked)
        ranked = [r for r in ranked if r.get("llm_recommendation") != "not_a_fit"]
        dropped = before - len(ranked)
        if dropped:
            print(f"[judge] Dropped {dropped} job(s) the LLM judge flagged as not_a_fit.")
    else:
        print("\n[judge] Skipped: set GROQ_API_KEY to enable the LLM judge stage.")

    if not ranked:
        print("\nAll stage-1 matches were flagged as not_a_fit by the LLM judge. Nothing to shortlist.")
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
