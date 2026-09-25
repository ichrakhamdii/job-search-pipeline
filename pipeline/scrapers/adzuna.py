import os
import requests

# Fallback only - see embedder.py's DEFAULT_API_KEY comment. A multi-user server MUST pass
# app_id/app_key explicitly on every call instead of relying on this.
# Free API key: https://developer.adzuna.com/
DEFAULT_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
DEFAULT_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
DEFAULT_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "gb")  # e.g. gb, us, fr, de


def is_configured(app_id: str | None = None, app_key: str | None = None) -> bool:
    return bool((app_id or DEFAULT_APP_ID) and (app_key or DEFAULT_APP_KEY))


def fetch_jobs(query: str = "machine learning engineer", limit: int = 50,
               app_id: str | None = None, app_key: str | None = None,
               country: str | None = None) -> list[dict]:
    """Pull jobs from Adzuna's official public API. Requires an app_id/app_key pair.

    app_id/app_key: pass explicitly in any multi-user context. Fall back to
    ADZUNA_APP_ID/ADZUNA_APP_KEY from the environment for single-user CLI use.
    """
    app_id = app_id or DEFAULT_APP_ID
    app_key = app_key or DEFAULT_APP_KEY
    country = country or DEFAULT_COUNTRY
    if not is_configured(app_id, app_key):
        return []

    jobs = []
    page = 1
    while len(jobs) < limit:
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 50,
            "what": query,
            "content-type": "application/json",
        }
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break
        for item in results:
            jobs.append({
                "title": item.get("title", ""),
                "company": (item.get("company") or {}).get("display_name", ""),
                "location": (item.get("location") or {}).get("display_name", ""),
                "description": item.get("description", ""),
                "url": item.get("redirect_url", ""),
                "source": "Adzuna",
                "posted_at": item.get("created", ""),
            })
            if len(jobs) >= limit:
                break
        page += 1
        if page > 5:
            break
    return jobs
