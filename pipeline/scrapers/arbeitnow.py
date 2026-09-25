import time
import requests

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 8


def fetch_jobs(query: str = "", limit: int = 100) -> list[dict]:
    """Pull jobs from Arbeitnow's public job board API (paginated, capped to avoid rate limits)."""
    jobs = []
    url = API_URL
    pages_fetched = 0
    while url and len(jobs) < limit and pages_fetched < MAX_PAGES:
        resp = requests.get(url, timeout=20)
        pages_fetched += 1
        if resp.status_code == 429:
            print("[arbeitnow] Rate limited, stopping pagination early.")
            break
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("data", []):
            title = item.get("title", "")
            description = item.get("description", "") or ""
            tags = " ".join(item.get("tags", []) or [])
            text = f"{title} {tags} {description}"
            if query and query.lower() not in text.lower():
                continue
            jobs.append({
                "title": title,
                "company": item.get("company_name", ""),
                "location": "Remote" if item.get("remote") else item.get("location", ""),
                "description": f"{tags}\n{description}",
                "url": item.get("url", ""),
                "source": "Arbeitnow",
                "posted_at": item.get("created_at", ""),
            })
            if len(jobs) >= limit:
                break
        url = data.get("links", {}).get("next")
        if url:
            time.sleep(0.5)
    return jobs
