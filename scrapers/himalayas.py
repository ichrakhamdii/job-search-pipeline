import requests

API_URL = "https://himalayas.app/jobs/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-pipeline; personal use)"}
PAGE_SIZE = 20
MAX_PAGES = 8  # capped to avoid pulling through the entire 100k+ catalog every run


def fetch_jobs(query: str = "", limit: int = 150) -> list[dict]:
    """Pull jobs from Himalayas' public JSON API (worldwide remote jobs, no key required).
    The API ignores server-side search, so results are paginated via cursor and filtered locally.
    """
    jobs = []
    cursor = None
    for _ in range(MAX_PAGES):
        if len(jobs) >= limit:
            break
        params = {"limit": PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        page_jobs = data.get("jobs", [])
        if not page_jobs:
            break
        for item in page_jobs:
            title = item.get("title", "")
            description = item.get("description", "") or item.get("excerpt", "") or ""
            categories = " ".join(item.get("categories", []) or [])
            text = f"{title} {categories} {description}"
            if query and query.lower() not in text.lower():
                continue
            locations = item.get("locationRestrictions") or []
            jobs.append({
                "title": title,
                "company": item.get("companyName", ""),
                "location": ", ".join(locations) if locations else "Remote (Worldwide)",
                "description": f"{categories}\n{description}",
                "url": item.get("applicationLink") or item.get("guid", ""),
                "source": "Himalayas",
                "posted_at": item.get("pubDate", ""),
            })
            if len(jobs) >= limit:
                break
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return jobs
