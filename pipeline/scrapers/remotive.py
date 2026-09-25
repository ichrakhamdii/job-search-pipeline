import requests

API_URL = "https://remotive.com/api/remote-jobs"
HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-pipeline; personal use)"}


def fetch_jobs(query: str = "", limit: int = 100) -> list[dict]:
    """Pull jobs from Remotive's public JSON API (worldwide remote jobs, no key required)."""
    resp = requests.get(API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title", "")
        description = item.get("description", "") or ""
        tags = " ".join(item.get("tags", []) or [])
        text = f"{title} {tags} {description}"
        if query and query.lower() not in text.lower():
            continue
        jobs.append({
            "title": title,
            "company": item.get("company_name", ""),
            "location": item.get("candidate_required_location", "Remote"),
            "description": f"{tags}\n{description}",
            "url": item.get("url", ""),
            "source": "Remotive",
            "posted_at": item.get("publication_date", ""),
        })
        if len(jobs) >= limit:
            break
    return jobs
