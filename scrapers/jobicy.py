import requests

API_URL = "https://jobicy.com/api/v2/remote-jobs"
HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-pipeline; personal use)"}
FETCH_COUNT = 200


def fetch_jobs(query: str = "", limit: int = 200) -> list[dict]:
    """Pull jobs from Jobicy's public JSON API (worldwide remote jobs, no key required)."""
    resp = requests.get(API_URL, params={"count": FETCH_COUNT}, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("jobs", []):
        title = item.get("jobTitle", "")
        description = item.get("jobDescription", "") or item.get("jobExcerpt", "") or ""
        industries = " ".join(item.get("jobIndustry", []) or [])
        text = f"{title} {industries} {description}"
        if query and query.lower() not in text.lower():
            continue
        jobs.append({
            "title": title,
            "company": item.get("companyName", ""),
            "location": item.get("jobGeo", "Remote"),
            "description": f"{industries}\n{description}",
            "url": item.get("url", ""),
            "source": "Jobicy",
            "posted_at": item.get("pubDate", ""),
        })
        if len(jobs) >= limit:
            break
    return jobs
