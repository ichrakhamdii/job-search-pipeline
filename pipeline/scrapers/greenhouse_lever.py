import os
import re
import requests

# Fallback only - see embedder.py's DEFAULT_API_KEY comment. A multi-user server should pass
# company lists explicitly per user instead of relying on this shared default.
# Comma-separated company board slugs, e.g. "stripe,notion,scale-ai"
DEFAULT_GREENHOUSE_COMPANIES = [c.strip() for c in os.environ.get("GREENHOUSE_COMPANIES", "").split(",") if c.strip()]
DEFAULT_LEVER_COMPANIES = [c.strip() for c in os.environ.get("LEVER_COMPANIES", "").split(",") if c.strip()]


def _strip_html(html: str) -> str:
    return re.sub("<[^<]+?>", " ", html or "")


def _fetch_greenhouse(company: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        return []
    jobs = []
    for item in resp.json().get("jobs", []):
        jobs.append({
            "title": item.get("title", ""),
            "company": company,
            "location": (item.get("location") or {}).get("name", ""),
            "description": _strip_html(item.get("content", "")),
            "url": item.get("absolute_url", ""),
            "source": "Greenhouse",
            "posted_at": item.get("updated_at", ""),
        })
    return jobs


def _fetch_lever(company: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        return []
    jobs = []
    for item in resp.json():
        jobs.append({
            "title": item.get("text", ""),
            "company": company,
            "location": (item.get("categories") or {}).get("location", ""),
            "description": _strip_html(item.get("descriptionPlain") or item.get("description", "")),
            "url": item.get("hostedUrl", ""),
            "source": "Lever",
            "posted_at": item.get("createdAt", ""),
        })
    return jobs


def fetch_jobs(query: str = "", limit: int = 200, greenhouse_companies: list[str] | None = None,
               lever_companies: list[str] | None = None) -> list[dict]:
    """Pull jobs from configured Greenhouse/Lever company boards (public read APIs, no key needed).

    greenhouse_companies/lever_companies: pass explicitly in any multi-user context (each user
    may want to track different companies). Fall back to GREENHOUSE_COMPANIES/LEVER_COMPANIES
    from the environment for single-user CLI use.
    """
    greenhouse_companies = greenhouse_companies if greenhouse_companies is not None else DEFAULT_GREENHOUSE_COMPANIES
    lever_companies = lever_companies if lever_companies is not None else DEFAULT_LEVER_COMPANIES

    jobs = []
    for company in greenhouse_companies:
        jobs.extend(_fetch_greenhouse(company))
    for company in lever_companies:
        jobs.extend(_fetch_lever(company))

    if query:
        q = query.lower()
        jobs = [j for j in jobs if q in f"{j['title']} {j['description']}".lower()]

    if not greenhouse_companies and not lever_companies:
        print("[greenhouse_lever] Skipped: no company slugs configured.")

    return jobs[:limit]
