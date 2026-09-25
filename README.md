# Job Search Pipeline

Scrapes multiple job boards, scores each posting against a candidate profile, re-ranks with semantic embeddings, and runs an LLM judge that catches false positives — producing a ranked shortlist of only new, genuinely relevant offers. Two ways to use it: a single-user **CLI** that runs locally, or a multi-user **web app** (accounts, async search, application tracking, AI-generated tailored CVs/cover letters/interview prep).

Neither mode auto-applies. Both stop at "here's your shortlist" — you review and apply yourself.

## Why I built this

Scrolling through half a dozen job boards every day, without knowing if a posting actually matches my skills until I click into it, wastes hours. A lot of what shows up is also stale — listings that have been "open" for months, roles quietly already filled, or postings padded with keywords to look more relevant than they really are. I wanted something that does that scanning for me: pull from multiple sources at once, score each posting against my actual skills, experience, and projects instead of just a title keyword match, and only surface what's genuinely new and above a real match bar.

## Structure

```
job-search-pipeline/
├── pipeline/          # Shared logic: scraping, matching, embeddings, LLM judge, CV extraction, generation
│   └── scrapers/          # One module per job source
├── backend/           # FastAPI web API - accounts, async job search, tracking, generation
│   └── app/{api, core, models, schemas, services, workers}
├── frontend/          # React (Vite + TypeScript) web app
│   └── src/{components, context, features, services}
├── main.py            # CLI: run the pipeline directly
├── build_profile.py   # CLI: build a profile from a CV PDF
├── profile/            # Local candidate_profile.json (CLI only, gitignored)
└── docker-compose.yml   # Optional local container setup for the backend/worker
```

`pipeline/` is the single implementation of the actual matching logic — both the CLI and the backend import from it directly, so there's one place scraping/scoring/judging behavior lives, not two copies to keep in sync.

## How matching works (shared by the CLI and the web app)

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
                                                    ranked shortlist (new matches only)
```

1. **Scrape** — pulls live postings from up to 8 sources, filtered by target job titles.
2. **Deduplicate against history** — only jobs never seen in a previous run are carried forward, so re-running never re-surfaces stale listings.
3. **Score every profile facet** — skills, experience, projects, certifications, and education are each scored independently and combined with configurable weights; only jobs above a match threshold survive.
4. **Semantic re-ranking** — Voyage AI embeddings catch synonyms plain keyword matching misses ("computer vision" ≈ "image recognition"); falls back to TF-IDF if no embeddings key is set.
5. **LLM judge** — a free open-weight model (via Groq) re-evaluates the shortlist for fit, seniority match, and whether a posting's visa-sponsorship claim looks genuine. A clear rejection removes the job from the shortlist.
6. **International-friendliness flags** — every surviving job is tagged for visa sponsorship, international-candidate language, and remote-friendliness.

### Job sources

| Source | API key required |
|---|---|
| RemoteOK, Arbeitnow, We Work Remotely, Remotive, Jobicy, Himalayas | No |
| Adzuna | Yes (free) — real search engine, by far the largest pool |
| Greenhouse / Lever | No key, but needs company slugs you configure |

Every source degrades gracefully when unconfigured — the pipeline still runs with a smaller pool.

## CLI

```bash
pip install -r requirements.txt
cp .env.example .env                      # add whichever API keys you have
python build_profile.py your_cv.pdf       # build a profile from your CV (any language, OCR fallback for scans)
python main.py                             # run a search, writes output/shortlist_<timestamp>.csv
```

Nothing is required to run it at all — every stage falls back or skips cleanly without a key. Voyage + Groq give real match quality; Adzuna adds volume.

**Scheduling** — meant to run unattended, not triggered manually each time. Windows: `run_pipeline.ps1` + `schtasks`. macOS/Linux: a cron entry calling `python main.py`.

## Web app

`backend/` (FastAPI) and `frontend/` (React) turn the same pipeline into a multi-user service:

- **Accounts** — email/password signup, JWT auth
- **Profile** — CV upload (same extraction logic as the CLI) or manual entry, stored per-user in Postgres
- **Async job search** — a real run takes several minutes under free-tier rate limits, so it runs as a Celery background task; the frontend polls for completion instead of blocking
- **Application tracking** — mark jobs saved/applied/interviewing/offer/rejected
- **Document generation** — tailored CV summary, cover letter, and mock interview prep per job description, grounded in the real profile (not generic filler)

API keys (Voyage/Groq/Adzuna) are bring-your-own — entered in the UI, stored only in the browser, never on the server.

See `backend/README.md` and `frontend/README.md` for setup. `docs/WEBAPP_PLAN.md` tracks what's built versus still in progress.

## License

MIT — see [LICENSE](LICENSE).
