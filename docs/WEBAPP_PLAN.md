# Web App Plan

Turn this from a locally-run CLI pipeline into a hosted, multi-user web app with real accounts: sign up, upload a CV, get a ranked job shortlist, generate tailored application material per job, and track applications over time — all persisted, all accessible from any device.

*(Revision note: an earlier version of this plan proposed Streamlit for speed of delivery. That's been superseded by the stack below — a real FastAPI + React/Postgres + Docker architecture — which fits the full feature set much better, especially application tracking and per-user history, both of which need real persistence that Streamlit's stateless model can't give cleanly.)*

## Goal

Someone with zero coding background should be able to:
1. Sign up / log in
2. Upload their CV (or fill a short form)
3. Click "Find Jobs" and see a ranked, sortable results table
4. Pick a job and get a tailored CV + cover letter for it
5. Get mock interview questions and a technical test matching that job
6. Mark jobs as applied and track status over time
7. Come back later, from any device, and see all of the above still there

## Architecture

```
 Next.js frontend (Vercel)  ──HTTPS/REST──▶  FastAPI backend (Docker)  ──▶  PostgreSQL
                                                    │
                                                    ▼
                                    scrapers/ · matcher.py · embedder.py
                                    judge.py · cv_extractor.py · groq_client.py
                                    (existing pipeline modules, reused as-is)
```

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js (React)** | Real component-based UI, full control over look and feel — this is where "beautiful" actually comes from, vs. Streamlit's fixed widget set. |
| Frontend hosting | **Vercel free tier** | Built by the Next.js team, zero-config deploys from a GitHub branch, generous free tier that stays free indefinitely for a personal-scale project. |
| Backend | **FastAPI (Python)** | Every existing pipeline module (`scrapers/`, `matcher.py`, `embedder.py`, `judge.py`, `cv_extractor.py`, `groq_client.py`) gets reused as an internal library, not rewritten — FastAPI just wraps it in REST endpoints. |
| Backend packaging | **Docker** | Used for the production build/deploy (Render builds the image from the `Dockerfile`) and available locally if wanted — but not required locally, see below. |
| Local dev | **`uvicorn` directly, against a free Neon dev database** | No local disk budget for Docker Desktop + a Postgres image + growing volumes. FastAPI runs as a plain Python process; `DATABASE_URL` points at a small free Neon project instead of a local Postgres container. Zero local Postgres footprint, and dev already matches production's real database engine (Postgres, not a SQLite stand-in that could hide type differences). |
| Database | **PostgreSQL (Neon, both dev and prod)** | Real relational storage for users, profiles, job history, applications, and generated documents — replaces today's flat JSON files (`seen_jobs.json`, `candidate_profile.json`) with per-user rows. One free Neon project can hold a `dev` branch and a `prod` branch, so local development and production stay on the same engine without ever installing Postgres locally. |
| Auth | **FastAPI-native (email + password + JWT)** | Full ownership, no third-party lock-in, consistent with the rest of the stack. `passlib`/`bcrypt` for password hashing, short-lived access tokens + refresh tokens. (NextAuth.js or Supabase Auth would be faster to bolt on, but hand rolling this keeps everything in one stack you fully control — flagged as an open decision below if you'd rather move faster.) |

### Being honest about "free" once we're self-hosting

Streamlit Community Cloud was free with zero caveats. A Dockerized FastAPI + Postgres backend needs somewhere to actually run in production, and that's where "free" gets nuanced:

- **Backend hosting** — **Render** free tier can run a Dockerized web service, but free instances spin down after ~15 minutes of inactivity (the next request wakes it up with a several-second cold start). **Fly.io** has a small free allowance with no forced sleep, but tighter resource limits. **Railway** supports Docker well but moved off a truly-free tier to usage-based credits — usable, but budget a few dollars/month once past the trial credit, not indefinitely free.
- **Database hosting** — running Postgres *itself* in a Docker container on a free host is fine for local dev, but unreliable for production (free container hosts rarely give a persistent volume that survives redeploys/restarts), and costs local disk during development that isn't always available. **Neon** (serverless Postgres, generous free tier, no time limit, branchable) sidesteps both problems — it's used for local dev *and* production, just as two different branches/projects.

**Recommendation:** Vercel (frontend) + Render (backend) + Neon (database, dev + prod) as the most reliably-free combination, with zero required local installs beyond Python itself. Docker stays relevant only for the production build Render runs — you don't need Docker Desktop running on your own machine at all to develop.

## Data model (rough)

- **users** — id, email, hashed_password, created_at
- **profiles** — id, user_id (FK), name, location, years_experience, target_titles, skills, experience, projects, education, certifications, languages, updated_at *(one row per user, replaces `candidate_profile.json`)*
- **seen_jobs** — id, user_id (FK), job_fingerprint, title, company, first_seen_at *(replaces the local `seen_jobs.json`, now per-user instead of per-machine)*
- **shortlist_results** — id, user_id (FK), run_at, job data + scores (per-run results, so past searches stay visible)
- **applications** — id, user_id (FK), job_fingerprint, status (`saved` / `applied` / `interviewing` / `offer` / `rejected`), applied_at, notes, updated_at
- **generated_documents** — id, user_id (FK), job_fingerprint, type (`tailored_cv` / `cover_letter` / `interview_prep`), content, created_at *(so past generations aren't lost — a real advantage of having accounts)*

## API surface (rough)

- `POST /auth/signup`, `POST /auth/login`, `POST /auth/refresh`
- `POST /profile` (from CV upload, reusing `cv_extractor.py` + the extraction logic in `build_profile.py`) or manual form; `GET /profile`
- `POST /jobs/search` — runs the scrape → score → judge pipeline for the signed-in user; `GET /jobs/results` — past run history
- `POST /applications`, `GET /applications`, `PATCH /applications/{id}` — tracking
- `POST /documents/tailor-cv`, `POST /documents/cover-letter`, `POST /documents/mock-interview`; `GET /documents` — generation history

## Phases

**Phase 1 — Backend foundations**
FastAPI app skeleton, Postgres schema + Alembic migrations, run locally with `uvicorn` against a free Neon dev database (no local Postgres/Docker required). Refactor the existing pipeline modules into an importable service layer with no reliance on `.env`/module-level constants at import time — the same multi-user-safety issue flagged in the original plan applies here too, just inside FastAPI request handlers instead of Streamlit session state.

**Phase 2 — Auth**
Signup/login/JWT issuance and refresh, password hashing, protected-route middleware.

**Phase 3 — Core pipeline API**
CV upload → profile extraction endpoint, profile CRUD, job search endpoint wrapping the existing scrape/match/judge pipeline, results persisted per-user in Postgres.

**Phase 4 — Next.js frontend MVP**
Signup/login pages, CV upload flow, results table (sortable, filterable), deployed to Vercel and talking to the FastAPI backend over REST.

**Phase 5 — Deploy backend + database**
Stand up Render (backend) + Neon (database) for production, wire CORS and environment variables between Vercel and the hosted backend.

**Phase 6 — Tailored CV & cover letter generator**
New endpoint + UI: paste or pick a job description → Groq-generated tailored summary/emphasis + cover letter, grounded in the user's real experience (not generic filler). Saved to `generated_documents` so it's not lost after the session. MVP output as Markdown/plain text; a `.docx` export (via `python-docx`) is a natural polish step once this works.

**Phase 7 — Mock interview questions & technical test generator**
Same generation pattern as Phase 6, new prompt/schema. Scope stays at question generation + guidance — not an auto-graded coding sandbox, which is a materially larger project (would need something like Judge0) and isn't warranted unless there's real demand for it later.

**Phase 8 — Application tracker**
Now genuinely simple given real accounts + Postgres — no local export/import workaround needed, unlike in the Streamlit version of this plan. Mark jobs as applied/interviewing/offer/rejected with notes, list and filter by status.

**Phase 9 — Polish**
Custom theming, friendly error/empty states, mobile responsiveness, and — if the BYOK decision below changes — per-user usage quotas against shared API keys.

## Open decisions (recommendations marked, but these are yours to confirm)

1. **API keys: BYOK vs. shared keys with quotas.** With real accounts and a database, you *could* front Voyage/Groq/Adzuna with your own keys and track per-user usage/caps in Postgres, which is far more turnkey for a visitor than making them go get three free API keys themselves. Recommend still starting **BYOK** for the MVP (avoids you being liable for cost/abuse before the product is validated), and revisiting shared-keys-with-quotas once there's real usage data suggesting people want the friction removed.
2. **Auth approach.** Recommend FastAPI-native JWT auth for full ownership. If you'd rather move faster and don't mind a dependency, NextAuth.js (frontend-side, supports Google/GitHub login easily) or Supabase Auth (bundles with a free Postgres too) would cut real implementation time.
3. **Production hosting combo.** Recommend Vercel + Render + Neon (above) as the most reliably free. Railway is a fine alternative if a small monthly cost is acceptable.
4. **Keep the CLI tool alive alongside the web app.** Recommend yes — the pipeline logic should live in one shared service layer that both the CLI (`main.py`) and the FastAPI backend import from, so there's no duplicated matching/scoring logic to keep in sync.
5. **How far to take the technical test generator.** Recommend questions + guidance only (see Phase 7), not a real execution sandbox, unless demand justifies that separately-sized project later.

## What's not changing

The scraping sources, scoring logic (5-facet weighting), embeddings, and LLM judge stay exactly as they are today. This plan is about giving the pipeline a real multi-user home with accounts and persistence, and layering three new generation/tracking features on top — not about changing how matching itself works.
