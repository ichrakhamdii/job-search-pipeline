import os
import requests

# Free API key: https://developer.adzuna.com/
APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
COUNTRY = os.environ.get("ADZUNA_COUNTRY", "gb")  # e.g. gb, us, fr, de


def is_configured() -> bool:
    return bool(APP_ID and APP_KEY)


def fetch_jobs(query: str = "machine learning engineer", limit: int = 50) -> list[dict]:
    """Pull jobs from Adzuna's official public API. Requires ADZUNA_APP_ID / ADZUNA_APP_KEY."""
    if not is_configured():
        return []

    jobs = []
    page = 1
    while len(jobs) < limit:
        url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/{page}"
        params = {
            "app_id": APP_ID,
            "app_key": APP_KEY,
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
