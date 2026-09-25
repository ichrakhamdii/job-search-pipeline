"""Shared pipeline orchestration: scrape -> dedupe -> score -> judge.

This is the one place the scrape/match/judge flow is implemented. Both the CLI (main.py,
single user, reads keys from .env) and the FastAPI backend (multi-user, reads keys per
request) call run_pipeline() instead of duplicating this logic - this is what keeps the
CLI and the web app's results identical and avoids maintaining two copies of the same flow.
"""
from datetime import datetime, timezone

from .scrapers import remoteok, arbeitnow, weworkremotely, adzuna, greenhouse_lever, remotive, jobicy, himalayas
from .matcher import rank_jobs, MIN_MATCH_SCORE
from .judge import judge_jobs, is_configured as judge_configured

# Adzuna supports real server-side search ("what=" param), so it's worth querying once per
# target title to get genuinely targeted results. The others return their whole catalog
# regardless of query, so we fetch each once and filter locally against all target titles
# instead of re-hitting their APIs (and their rate limits) once per title.
TITLE_ITERATED_SOURCES = [adzuna]
FETCH_ONCE_SOURCES = [remoteok, arbeitnow, weworkremotely, greenhouse_lever, remotive, jobicy, himalayas]


def job_fingerprint(job: dict) -> str:
    if job.get("url"):
        return job["url"].strip().lower()
    return f"{job.get('title','').strip().lower()}|{job.get('company','').strip().lower()}"


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


def collect_jobs(titles: list[str], api_keys: dict, log=print) -> list[dict]:
    """api_keys may contain: adzuna_app_id, adzuna_app_key, greenhouse_companies (list[str]),
    lever_companies (list[str]). Any missing key just means that source is skipped.
    """
    all_jobs = []

    adzuna_app_id = api_keys.get("adzuna_app_id")
    adzuna_app_key = api_keys.get("adzuna_app_key")
    for source in TITLE_ITERATED_SOURCES:
        name = source.__name__.split(".")[-1]
        if not source.is_configured(adzuna_app_id, adzuna_app_key):
            log(f"[{name}] Skipped: not configured (missing API credentials).")
            continue
        for title in titles:
            try:
                jobs = source.fetch_jobs(query=title, app_id=adzuna_app_id, app_key=adzuna_app_key)
                log(f"[{name}] '{title}': fetched {len(jobs)} jobs")
                all_jobs.extend(jobs)
            except Exception as e:
                log(f"[{name}] '{title}' ERROR: {e}")

    greenhouse_companies = api_keys.get("greenhouse_companies")
    lever_companies = api_keys.get("lever_companies")
    for source in FETCH_ONCE_SOURCES:
        name = source.__name__.split(".")[-1]
        try:
            if source is greenhouse_lever:
                jobs = source.fetch_jobs(query="", greenhouse_companies=greenhouse_companies,
                                          lever_companies=lever_companies)
            else:
                jobs = source.fetch_jobs(query="")
            matched = [j for j in jobs if job_matches_any_title(j, titles)]
            log(f"[{name}] fetched {len(jobs)} jobs, {len(matched)} matched target titles")
            all_jobs.extend(matched)
        except Exception as e:
            log(f"[{name}] ERROR: {e}")

    return dedupe(all_jobs)


def run_pipeline(profile: dict, titles: list[str], seen: dict, api_keys: dict,
                  top_n: int = 50, log=print) -> list[dict]:
    """Run the full scrape -> dedupe -> score -> judge pipeline for one user.

    api_keys may contain: voyage_api_key, groq_api_key, adzuna_app_id, adzuna_app_key,
    greenhouse_companies, lever_companies. Any missing key degrades that stage gracefully
    (smaller job pool, TF-IDF fallback instead of embeddings, or no LLM judge pass) - never
    reads from process-wide environment variables or module-level defaults, so this is safe
    to call concurrently for different users with different keys.

    seen: the caller's job-fingerprint history (e.g. a per-user DB row's data, or a local
    JSON file for the CLI) - mutated in place with newly-seen jobs.

    Returns the ranked, judge-filtered list of new jobs (empty list if nothing qualified).
    """
    jobs = collect_jobs(titles, api_keys, log=log)
    log(f"Total unique jobs collected this run: {len(jobs)}")

    new_jobs = filter_new_jobs(jobs, seen)
    log(f"New jobs since last run: {len(new_jobs)}")
    if not new_jobs:
        return []

    voyage_api_key = api_keys.get("voyage_api_key")
    ranked = rank_jobs(profile, new_jobs, top_n=top_n, voyage_api_key=voyage_api_key)
    if not ranked:
        log(f"No new offers reached the {MIN_MATCH_SCORE:.0f}% match threshold this run.")
        return []

    groq_api_key = api_keys.get("groq_api_key")
    if judge_configured(groq_api_key):
        log(f"Running LLM judge on {len(ranked)} shortlisted jobs...")
        verdicts = judge_jobs(profile, ranked, api_key=groq_api_key)
        for idx, row in enumerate(ranked):
            v = verdicts.get(idx, {})
            row["llm_recommendation"] = v.get("recommendation", "")
            row["llm_rationale"] = v.get("rationale", "")
            row["llm_seniority_fit"] = v.get("seniority_fit", "")
            row["llm_visa_claim_credible"] = v.get("visa_claim_credible", "")
            row["llm_confidence"] = v.get("confidence", "")

        # A clear "not_a_fit" verdict should actually drop the job, not just annotate it -
        # that's the point of running a second, more careful pass over the shortlist.
        before = len(ranked)
        ranked = [r for r in ranked if r.get("llm_recommendation") != "not_a_fit"]
        dropped = before - len(ranked)
        if dropped:
            log(f"[judge] Dropped {dropped} job(s) the LLM judge flagged as not_a_fit.")
    else:
        log("[judge] Skipped: no Groq API key configured.")

    return ranked
