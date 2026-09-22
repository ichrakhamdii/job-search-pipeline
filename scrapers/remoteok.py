import requests

API_URL = "https://remoteok.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-pipeline; personal use)"}


def fetch_jobs(query: str = "", limit: int = 100) -> list[dict]:
    """Pull jobs from RemoteOK's public JSON API and optionally filter by keyword."""
    resp = requests.get(API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data:
        if not isinstance(item, dict) or "position" not in item:
            continue  # first element is metadata, not a job
        title = item.get("position", "")
        description = item.get("description", "") or ""
        tags = " ".join(item.get("tags", []) or [])
        text = f"{title} {tags} {description}"
        if query and query.lower() not in text.lower():
            continue
        jobs.append({
            "title": title,
            "company": item.get("company", ""),
            "location": item.get("location", "Remote"),
            "description": f"{tags}\n{description}",
            "url": item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
            "source": "RemoteOK",
            "posted_at": item.get("date", ""),
        })
        if len(jobs) >= limit:
            break
    return jobs
