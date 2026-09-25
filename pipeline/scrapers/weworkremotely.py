import feedparser

FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-data-jobs.rss",
]


def fetch_jobs(query: str = "", limit: int = 100) -> list[dict]:
    """Pull jobs from We Work Remotely's public RSS feeds."""
    jobs = []
    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title_raw = entry.get("title", "")
            # WWR titles are formatted "Company: Job Title"
            company, _, title = title_raw.partition(": ")
            if not title:
                title, company = company, ""
            description = entry.get("summary", "") or ""
            text = f"{title} {description}"
            if query and query.lower() not in text.lower():
                continue
            jobs.append({
                "title": title.strip(),
                "company": company.strip(),
                "location": "Remote",
                "description": description,
                "url": entry.get("link", ""),
                "source": "WeWorkRemotely",
                "posted_at": entry.get("published", ""),
            })
            if len(jobs) >= limit:
                break
    return jobs
