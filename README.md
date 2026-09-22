# Job Search Pipeline

A personal job-search automation pipeline: it scrapes multiple job boards, scores each posting against your resume/profile across five weighted facets, re-ranks the shortlist with semantic embeddings, and runs the survivors through an LLM judge that catches false positives and flags visa/remote signals. The output is a ranked CSV of only new, genuinely relevant offers — not a wall of noise.

It is not an auto-apply bot. It stops at "here's your shortlist" — you still review and apply yourself.

## How it works

```
 8 job sources ──▶ title filter ──▶ dedup vs. history ──▶ 5-facet scoring
                                                                │
                                                                ▼
                                            embeddings re-rank (Voyage AI, ≥ threshold)
                                                                │
                                                                ▼
                                                LLM judge (Groq) drops false positives
                                                                │
                                                                ▼
                                              ranked shortlist.csv (new matches only)
```

1. **Scrape** — pulls live postings from up to 8 sources, filtered by your target job titles.
2. **Deduplicate against history** — only jobs never seen in a previous run are carried forward (`output/seen_jobs.json`), so re-running never re-surfaces stale listings.
3. **Score every profile facet** — skills, experience, projects, certifications, and education are each scored independently and combined with configurable weights; only jobs above a match threshold survive.
4. **Semantic re-ranking** — Voyage AI embeddings catch synonyms plain keyword matching misses ("computer vision" ≈ "image recognition"); falls back automatically to TF-IDF if no embeddings key is set.
5. **LLM judge** — a free open-weight model (via Groq) re-evaluates the shortlist for fit, seniority match, and whether a posting's visa-sponsorship claim looks genuine or is generic boilerplate. A clear rejection actually removes the job from the shortlist.
6. **International-friendliness flags** — every surviving job is tagged for visa sponsorship, international-candidate language, and remote-friendliness.

## Job sources

| Source | API key required | Notes |
|---|---|---|
| RemoteOK | No | Public JSON API |
| Arbeitnow | No | Public JSON API, paginated |
| We Work Remotely | No | Public RSS feeds |
| Remotive | No | Public JSON API |
| Jobicy | No | Public JSON API |
| Himalayas | No | Public JSON API, cursor-paginated |
| Adzuna | Yes (free) | Real search engine, by far the largest pool — queried once per target title |
| Greenhouse / Lever | No key, but needs company slugs | Per-company job boards; you supply which companies to track |

Every source degrades gracefully when unconfigured — the pipeline still runs, just with a smaller pool.

## Setup

**1. Clone and install dependencies**

```bash
git clone <this-repo-url>
cd job-search-pipeline
pip install -r requirements.txt
```

**2. Create your profile**

```bash
cp profile/candidate_profile.example.json profile/candidate_profile.json
```

Edit `profile/candidate_profile.json` with your own skills, experience, projects, certifications, education, and target job titles. This file is gitignored — your data stays local.

**3. Add your API keys**

```bash
cp .env.example .env
```

Fill in whichever keys you have (see the table in `.env.example` for where to get each one, free). Nothing is required to run the pipeline at all — every stage falls back or skips cleanly without a key — but Voyage + Groq are recommended for real match quality, and Adzuna for volume.

**4. Run it**

```bash
python main.py                      # uses your profile's target_titles
python main.py "extra search term"  # adds one more title on top of the profile's list
```

Output lands in `output/shortlist_<timestamp>.csv` — sorted by match score, with per-facet score breakdowns, the LLM judge's verdict and rationale, and international-hiring flags.

## Configuration reference

| Setting | Where | Default | Effect |
|---|---|---|---|
| `MIN_MATCH_SCORE` | `matcher.py` | 50% | Jobs below this are dropped before the LLM judge ever sees them |
| `CATEGORY_WEIGHTS` | `matcher.py` | skills 35% / experience 30% / projects 15% / certifications 10% / education 10% | How the five profile facets combine into one score |
| `VOYAGE_MODEL` | env var | `voyage-3.5` | Override if Voyage deprecates the default |
| `GROQ_MODEL` | env var | `openai/gpt-oss-120b` | Override if Groq deprecates the default (check `GET /openai/v1/models` for current options) |

## Scheduling

The pipeline is meant to run unattended on a recurring basis, not be triggered manually each time — matches accumulate as new postings appear.

**Windows** — `run_pipeline.ps1` is a ready-made wrapper that logs each run's output:

```powershell
schtasks /Create /TN "JobSearchPipeline" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File <path>\run_pipeline.ps1" /SC DAILY /ST 09:00
```

**macOS/Linux** — add a cron entry:

```
0 9 * * * cd /path/to/job-search-pipeline && python main.py >> output/run_log_$(date +\%F).txt 2>&1
```

## Cost

At typical shortlist sizes (a handful to a few dozen jobs per run):
- **Voyage AI**: free tier covers 200M tokens; unverified accounts are capped at 3 requests/min and 10K tokens/min (the pipeline handles this with automatic retry/backoff)
- **Groq**: free tier, no card required
- **Adzuna**: free tier, no card required

Realistic total cost for personal use: **$0**.

## A note on scraping

This project only uses documented public APIs and RSS feeds — no HTML scraping, no bypassing of authentication or rate limits. It deliberately does not support LinkedIn or Indeed, since scraping those violates their Terms of Service. If you add a new source, check that source's ToS first.

## License

MIT — see [LICENSE](LICENSE).
