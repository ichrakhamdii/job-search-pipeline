# Backend (FastAPI)

REST API for the job search pipeline: accounts, profiles (including CV upload), async job
search, application tracking, and AI-generated tailored CVs/cover letters/interview prep.

## Architecture

```
app/
├── api/v1/
│   ├── endpoints/     # auth.py, cv.py, jobs.py, tracking.py, documents.py - route handlers
│   └── api.py         # assembles all endpoint routers under one v1 router
├── core/               # config.py (Settings), security.py (JWT/password hashing), database.py
├── models/             # SQLAlchemy tables (one file per domain)
├── schemas/            # Pydantic request/response shapes
├── services/           # business logic + persistence, called by endpoints and workers alike
├── workers/            # Celery app + the async job-search task
└── main.py             # FastAPI app instance, CORS, router mounting
migrations/             # Alembic
```

The actual scraping/matching/judging/generation logic (`pipeline/` at the repo root) is
**not** duplicated here - `services/job_service.py` and `services/document_service.py` import
directly from it. That package is the single source of truth the CLI (`main.py`,
`build_profile.py`) and this backend both depend on.

## Why job search runs as a background task

A real run scrapes 8 sources, calls Voyage AI for embeddings, and runs a Groq LLM judge pass -
observed to take several minutes with free-tier rate limits. Running that synchronously inside
an HTTP request would block or time out. `POST /api/v1/jobs/search` instead enqueues a Celery
task and returns immediately with a task id; the client polls `GET /api/v1/jobs/search/{id}`
until `status` is `succeeded` or `failed`, then reads `GET /api/v1/jobs/results`.

## Local setup (no local database or broker needed)

Per this project's storage-constrained dev workflow (see `../docs/WEBAPP_PLAN.md`), local
development runs directly on the host - no Docker, no local Postgres, no local Redis.

1. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Create a free Neon Postgres project** at [neon.tech](https://neon.tech) - use a "dev"
   branch/project separate from production. Copy its connection string.

3. **Create a free Upstash Redis database** at [upstash.com](https://upstash.com) (used as the
   Celery broker/result backend). Copy its connection string (the `rediss://...` TLS URL).

4. **Configure `.env`**
   ```bash
   cp .env.example .env
   ```
   Fill in `DATABASE_URL` (from Neon), `REDIS_URL` (from Upstash), and generate a
   `JWT_SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

5. **Run the first migration** (creates all tables in your Neon dev database)
   ```bash
   alembic revision --autogenerate -m "initial schema"
   alembic upgrade head
   ```

6. **Run the API**
   ```bash
   uvicorn app.main:app --reload
   ```
   Interactive docs at `http://localhost:8000/docs`.

7. **Run the Celery worker** (separate terminal - required for `/jobs/search` to actually
   process; without it, tasks stay `pending` forever)
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info
   ```
   On Windows, Celery's default worker pool doesn't support this well - add `--pool=solo`.

## Production

`Dockerfile` builds this service; note the build **context must be the repo root**, not
`backend/`, since the image also needs the sibling `pipeline/` package:

```bash
docker build -f backend/Dockerfile -t job-copilot-backend .
```

Deploy the same image twice on your host of choice (see the root plan doc for the
Render/Neon/Upstash recommendation) - once as the web service (`uvicorn`), once as the worker
(override the command to the `celery worker` line above). Production Postgres and Redis should
be separate Neon/Upstash projects from your dev ones, not the same database.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/signup`, `/login`, `/refresh` | Auth |
| GET/PUT | `/api/v1/cv` | Read/replace your profile |
| POST | `/api/v1/cv/upload` | Build a profile from an uploaded CV PDF |
| POST | `/api/v1/jobs/search` | Kick off a background search run (202, returns a task id) |
| GET | `/api/v1/jobs/search/{task_id}` | Poll a search run's status |
| GET | `/api/v1/jobs/results` | Past shortlist results |
| POST/GET/PATCH | `/api/v1/tracking` | Application tracking |
| POST | `/api/v1/documents/tailor-cv`, `/cover-letter`, `/mock-interview` | AI-generated application material |
| GET | `/api/v1/documents` | Past generations |
