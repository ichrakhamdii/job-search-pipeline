# Job Search Pipeline

A personal job-search automation pipeline: it scrapes multiple job boards, scores each posting against your resume/profile across five weighted facets, re-ranks the shortlist with semantic embeddings, and runs the survivors through an LLM judge that catches false positives and flags visa/remote signals. The output is a ranked CSV of only new, genuinely relevant offers — not a wall of noise.

It is not an auto-apply bot. It stops at "here's your shortlist" — you still review and apply yourself.

## Why I built this

Scrolling through half a dozen job boards every day, without knowing if a posting actually matches my skills until I click into it, wastes hours. A lot of what shows up is also stale — listings that have been "open" for months, roles quietly already filled, or postings padded with keywords to look more relevant than they really are. I wanted something that does that scanning for me: pull from multiple sources at once, score each posting against my actual skills, experience, and projects instead of just a title keyword match, and only surface what's genuinely new and above a real match bar — not the same recycled listings every time I look.

## Why these technologies

- **LLM-based CV parsing instead of a traditional ATS parser.** Classic ATS resume parsers work by matching regex patterns against fixed section headers ("EXPERIENCE", "SKILLS", ...), which breaks the moment a CV uses a different layout, a different language, or an unconventional structure — and that's exactly what real CVs look like. Mine has a two-column certifications/languages section that trips up naive extraction. An LLM reads a CV the way a person would: it understands what a bullet point under a job title means regardless of formatting, and it works the same whether the CV is in English, French, or Arabic. I didn't want the accuracy of the whole pipeline to depend on how well my resume happened to match some parser's template assumptions.

- **Voyage AI embeddings for matching, not just keyword search.** Keyword/TF-IDF matching would call a "Computer Vision Engineer" posting a mismatch against "image recognition" experience just because the wording differs. Embeddings capture meaning, not spelling, so semantically equivalent skills get credit even when the exact terms don't line up.

- **A second LLM pass (the "judge") on top of the embedding score.** Embeddings alone still produce false positives — a posting can score high because the title matches while the actual role is completely different. (Caught a real one during testing: an "AI Engineer" listing that turned out to be Go-language video engineering work, nothing to do with ML.) The judge re-reads each shortlisted posting against my actual background and drops what doesn't really fit, instead of trusting one similarity number.

- **Groq instead of a paid API for the judge.** I wanted this to run without needing a credit card or ongoing spend, so I used Groq's free tier, which serves capable open-weight models fast and at no cost.

- **Multiple job sources instead of one.** No single board has everything, and some of the biggest ones (LinkedIn, Indeed) don't allow scraping under their Terms of Service. So the pipeline pulls from several public, key-free or free-tier APIs instead — more compliant, and broader coverage than any one source alone.

- **"New jobs only" tracking.** Re-running the pipeline shouldn't show the same postings every day. Every job is fingerprinted and remembered, so each run only surfaces what's actually changed since the last one.

- **Five separately weighted scoring facets instead of one blended number.** Skills, experience, projects, certifications, and education don't matter equally for every fit judgment, and lumping them into a single score hides *why* a job ranked the way it did. Scoring them separately, then combining with configurable weights, makes the ranking both more accurate and easier to sanity-check.

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

**2. Add your API keys**

```bash
cp .env.example .env
```

Fill in whichever keys you have (see the table in `.env.example` for where to get each one, free). Nothing is required to run the pipeline at all — every stage falls back or skips cleanly without a key — but Voyage + Groq are recommended for real match quality, and Adzuna for volume. `GROQ_API_KEY` is also what powers profile generation in the next step.

**3. Create your profile — from your CV, automatically**

```bash
python build_profile.py path/to/your_cv.pdf
```

This extracts the text from your CV and sends it to the LLM judge's model to structure it into `profile/candidate_profile.json` — skills, experience, projects, education, certifications, and inferred target job titles. It works with CVs in any language (French, Arabic, etc. are translated to English for consistent matching against English-language postings), and automatically falls back to OCR if the PDF is a scanned image rather than real text (this requires the Tesseract binary — see below).

The result is a first draft, not gospel: review `profile/candidate_profile.json` afterward and fix anything the extraction got wrong, especially around unusual PDF layouts (multi-column sections can occasionally cause a field to be misattributed).

Prefer to skip the CV upload entirely? Copy the template and fill it in by hand instead:

```bash
cp profile/candidate_profile.example.json profile/candidate_profile.json
```

Either way, this file is gitignored — your data stays local and is never committed.

**OCR prerequisite (only needed for scanned PDFs):** `pytesseract` is a wrapper around the Tesseract OCR engine, which is a separate system binary, not a Python package. If your CV has a real text layer (nearly all CVs made from Word/Google Docs/LaTeX do), OCR never triggers and you can skip this. If it does trigger, install Tesseract first: [Windows](https://github.com/UB-Mannheim/tesseract/wiki) · macOS (`brew install tesseract`) · Linux (`apt install tesseract-ocr`).

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
