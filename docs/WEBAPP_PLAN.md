# Web App Plan

Turn this from a locally-run CLI pipeline into a hosted, multi-user web app with real accounts: sign up, upload a CV, get a ranked job shortlist, generate tailored application material per job, and track applications over time — all persisted, all accessible from any device.

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
 React SPA (Vite+TS) frontend  ──HTTPS/REST──▶  FastAPI backend  ──▶  PostgreSQL (Neon)
                                            │        ▲
                                       enqueues       polls status
                                            ▼        │
                                      Celery worker ──┘
                                            │
                                            ▼
                              pipeline/ package (repo root, shared with the CLI):
                              scrapers/ · matcher.py · embedder.py · judge.py
                              cv_extractor.py · profile_builder.py · document_service.py
```

| Layer | Choice | Why |
|---|---|---|
| Frontend | **React SPA (Vite + TypeScript)** | Real component-based UI, full control over look and feel — this is where "beautiful" actually comes from, vs. Streamlit's fixed widget set. |
| Backend | **FastAPI (Python)**, `api/v1/endpoints` + `core`/`models`/`schemas`/`services`/`workers` layout | Standard, widely-used FastAPI production structure. `services/` are thin orchestration + persistence wrappers around `pipeline/` — the actual scraping/matching/judging/generation logic is **not** duplicated here, it's imported from the shared package both the CLI and this backend depend on. |
| Async job search | **Celery + Redis** | A real search run (8 sources, Voyage embeddings, Groq judge pass) takes several minutes under free-tier rate limits — running that inside an HTTP request would block or time out. `POST /jobs/search` enqueues a Celery task and returns a task id immediately; the client polls `GET /jobs/search/{id}` for status. |
| Backend packaging | **Docker** | Used for the production build/deploy and available locally if wanted — but not required locally, see below. Build context is the repo root (not `backend/`), since the image needs the sibling `pipeline/` package too. |
| Local dev | **`uvicorn` + a separate `celery worker` process, directly on the host** | No local disk budget for Docker Desktop + database/broker images + growing volumes. `DATABASE_URL` points at a free Neon dev project, `REDIS_URL` at a free Upstash Redis database — both cloud-hosted, so local dev needs nothing installed beyond Python packages. `docker-compose.yml` at the repo root is provided as an *optional* fully-containerized alternative for anyone with disk budget to spare, or for CI. |
| Database | **PostgreSQL (Neon, both dev and prod)** | Real relational storage for users, profiles, job history, applications, generated documents, and async task status — replaces today's flat JSON files (`seen_jobs.json`, `candidate_profile.json`) with per-user rows. One free Neon account can hold a `dev` project and a `prod` project, so local development and production stay on the same engine without ever installing Postgres locally. |
| Task queue broker | **Redis (Upstash free tier)** | Same reasoning as Neon for Postgres — serverless, no local install, free tier covers dev and a low-volume production workload. |
| Auth | **FastAPI-native (email + password + JWT)** | Full ownership, no third-party lock-in, consistent with the rest of the stack. `passlib`/`bcrypt` for password hashing, short-lived access tokens + refresh tokens. (NextAuth.js or Supabase Auth would be faster to bolt on, but hand rolling this keeps everything in one stack you fully control — flagged as an open decision below if you'd rather move faster.) |

### Frontend framework — decided: Vite + React + TypeScript SPA

Earlier drafts named Next.js/Vercel; settled on a Vite + TypeScript React SPA per the reference architecture, structured as `frontend/src/{components,context,features,services}`. Deploys just as freely to Vercel, Netlify, or Cloudflare Pages as Next.js would, since it's a plain static build talking to the backend over REST.

### Being honest about "free" once we're self-hosting

Streamlit Community Cloud was free with zero caveats. A Dockerized FastAPI + Postgres backend needs somewhere to actually run in production, and that's where "free" gets nuanced:

- **Backend hosting** — **Render** free tier can run a Dockerized web service, but free instances spin down after ~15 minutes of inactivity (the next request wakes it up with a several-second cold start). **Fly.io** has a small free allowance with no forced sleep, but tighter resource limits. **Railway** supports Docker well but moved off a truly-free tier to usage-based credits — usable, but budget a few dollars/month once past the trial credit, not indefinitely free.
- **Database hosting** — running Postgres *itself* in a Docker container on a free host is fine for local dev, but unreliable for production (free container hosts rarely give a persistent volume that survives redeploys/restarts), and costs local disk during development that isn't always available. **Neon** (serverless Postgres, generous free tier, no time limit, branchable) sidesteps both problems — it's used for local dev *and* production, just as two different branches/projects.

**Recommendation:** frontend host TBD (Vercel/Netlify/Cloudflare Pages, see above) + Render (backend + worker) + Neon (database, dev + prod) + Upstash (Redis, dev + prod) as the most reliably-free combination, with zero required local installs beyond Python itself. Docker stays relevant only for the production build Render runs — you don't need Docker Desktop running on your own machine at all to develop.

## Data model (rough)

- **users** — id, email, hashed_password, created_at
- **profiles** — id, user_id (FK), name, location, years_experience, target_titles, skills, experience, projects, education, certifications, languages, updated_at *(one row per user, replaces `candidate_profile.json`)*
- **seen_jobs** — id, user_id (FK), job_fingerprint, title, company, first_seen_at *(replaces the local `seen_jobs.json`, now per-user instead of per-machine)*
- **shortlist_results** — id, user_id (FK), run_at, job data + scores (per-run results, so past searches stay visible)
- **applications** — id, user_id (FK), job_fingerprint, status (`saved` / `applied` / `interviewing` / `offer` / `rejected`), applied_at, notes, updated_at
- **generated_documents** — id, user_id (FK), job_fingerprint, type (`tailored_cv` / `cover_letter` / `interview_prep`), content, created_at *(so past generations aren't lost — a real advantage of having accounts)*
- **search_tasks** — id, user_id (FK), celery_task_id, status (`pending`/`running`/`succeeded`/`failed`), error, created_at, finished_at *(lets the frontend poll an async search run's progress)*

## API surface (implemented — see `backend/README.md` for the full table)

- `POST /api/v1/auth/signup`, `/login`, `/refresh`
- `GET`/`PUT /api/v1/cv`, `POST /api/v1/cv/upload` (from CV upload, reusing `pipeline/cv_extractor.py` + `pipeline/profile_builder.py`)
- `POST /api/v1/jobs/search` (202, enqueues a Celery task) → `GET /api/v1/jobs/search/{task_id}` (poll) → `GET /api/v1/jobs/results`
- `POST/GET/PATCH /api/v1/tracking` — application tracking
- `POST /api/v1/documents/tailor-cv`, `/cover-letter`, `/mock-interview`; `GET /api/v1/documents` — generation history

## Phases

**Phase 1 — Backend foundations ✅ mostly built, pending a live database**
Done: the `pipeline/` package (scrapers, matcher, embedder, judge, cv_extractor, profile_builder, document_service, pipeline_service) now lives at the repo root as the single shared implementation; every function that touches an API key or per-user config (`embedder.embed_texts`, `groq_client.call_groq`, `judge.judge_jobs`, `matcher.rank_jobs`, `scrapers/adzuna.fetch_jobs`, `scrapers/greenhouse_lever.fetch_jobs`) now takes those as explicit parameters instead of reading module-level constants at import time — the multi-user-safety issue flagged earlier is fixed, verified via a real CLI run producing identical-quality results post-refactor. The FastAPI app (`backend/app/`) is fully scaffolded: `api/v1/endpoints` (auth, cv, jobs, tracking, documents), `core` (config/security/database), `models` (7 tables across 5 files), `schemas`, `services` (thin wrappers calling into `pipeline/`), and `workers` (Celery task for async search). Verified: the app imports cleanly, all 19 routes register, and `sqlalchemy.orm.configure_mappers()` confirms every relationship resolves (caught and fixed one real bug — `SeenJob` was missing its back-reference to `User` — before it ever hit a database). Alembic is wired up (`migrations/env.py` reads `DATABASE_URL` from settings) but the first migration hasn't been generated yet — that needs a real Neon connection string, which hasn't been provided in this session; hand-writing a migration without a live DB to verify it against would risk an unverified schema, so this is the one concrete next step.
Not done: no live Postgres or Redis has been connected, so nothing has been tested against a real database yet, and no auth/CV-upload/search flow has been exercised end-to-end through actual HTTP requests (only import-time and mapper-configuration checks so far).

**Phase 2 — Auth ✅ implemented, untested against a live DB**
Signup/login/refresh via `app/core/security.py` + `app/services/auth_service.py` + `app/api/v1/endpoints/auth.py`. Needs a real database to actually exercise.

**Phase 3 — Core pipeline API ✅ implemented, untested against a live DB**
CV upload → profile extraction (`app/services/profile_service.py`, reusing `pipeline/cv_extractor.py` + `pipeline/profile_builder.py` exactly as the CLI does), profile CRUD, async job search via Celery (`app/workers/tasks.py` → `app/services/job_service.py` → `pipeline/pipeline_service.py`), results persisted per-user in Postgres.

**Phase 3.5 — Application tracking & document generation ✅ implemented, untested against a live DB**
Originally scoped as later phases (6-8), but since the full backend was being built anyway, `app/services/application_service.py` and `app/services/document_service.py` (wrapping `pipeline/document_service.py`'s tailor_cv/cover_letter/mock_interview, verified working live against a real Groq key with genuinely grounded, non-generic output) are already in place alongside auth/profile/jobs.

**Phase 4 — Frontend MVP ✅ built, untested against a live backend**
`frontend/` (Vite + React + TypeScript) is scaffolded and structured per the reference architecture: `components/` (Button, Input, Card, Spinner, Table, ApiKeysForm, Layout), `context/` (AuthContext with JWT storage + auto-refresh-on-401, ThemeContext for light/dark), `features/auth` (Login, Register, ProtectedRoute), `features/dashboard` (search trigger with polling, ranked job table, application status board), `features/tailor` (CV upload, tailored-CV/cover-letter/interview-prep generation panel), `services/api.ts` (typed Axios client covering every backend endpoint) + `services/types.ts` (mirrors the backend Pydantic schemas). Verified: `npm run build` compiles with zero TypeScript errors.
Not done: no backend has been running during this build, so no real signup/login/search/generation flow has been exercised through the actual UI yet — only build-time verification so far.

**Phase 5 — Deploy backend + database + broker**
Stand up Render (backend + worker, two services from the same Docker image) + Neon (database) + Upstash (Redis) for production, wire CORS and environment variables to the frontend host.

**Phase 6 — Polish**
Custom theming, friendly error/empty states, mobile responsiveness, a `.docx` export for tailored CVs (via `python-docx`) instead of Markdown-only, and — if the BYOK decision below changes — per-user usage quotas against shared API keys. The technical-test generator scope stays at question generation + guidance, not an auto-graded coding sandbox (that would need something like Judge0 — a materially larger project, not warranted unless there's real demand for it).

## Open decisions (recommendations marked, but these are yours to confirm)

1. **API keys: BYOK vs. shared keys with quotas.** With real accounts and a database, you *could* front Voyage/Groq/Adzuna with your own keys and track per-user usage/caps in Postgres, which is far more turnkey for a visitor than making them go get three free API keys themselves. Recommend still starting **BYOK** for the MVP (avoids you being liable for cost/abuse before the product is validated), and revisiting shared-keys-with-quotas once there's real usage data suggesting people want the friction removed.
2. **Auth approach.** Recommend FastAPI-native JWT auth for full ownership. If you'd rather move faster and don't mind a dependency, NextAuth.js (frontend-side, supports Google/GitHub login easily) or Supabase Auth (bundles with a free Postgres too) would cut real implementation time.
3. **Production hosting combo.** Recommend Vercel + Render + Neon (above) as the most reliably free. Railway is a fine alternative if a small monthly cost is acceptable.
4. **Keep the CLI tool alive alongside the web app.** Recommend yes — the pipeline logic should live in one shared service layer that both the CLI (`main.py`) and the FastAPI backend import from, so there's no duplicated matching/scoring logic to keep in sync.
5. **How far to take the technical test generator.** Recommend questions + guidance only (see Phase 6), not a real execution sandbox, unless demand justifies that separately-sized project later.

## What's not changing

The scraping sources, scoring logic (5-facet weighting), embeddings, and LLM judge stay exactly as they are today. This plan is about giving the pipeline a real multi-user home with accounts and persistence, and layering three new generation/tracking features on top — not about changing how matching itself works.
