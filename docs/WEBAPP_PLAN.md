# Web App Plan

Turn this from a locally-run CLI pipeline into a hosted web app: upload a CV, get a ranked job shortlist in the browser, no git clone, no Python setup, no terminal.

## Goal

Someone with zero coding background should be able to:
1. Open a URL
2. Upload their CV (or fill a short form)
3. Paste a couple of free API keys (with links to get them)
4. Click "Find Jobs"
5. See a ranked, sortable results table and download it as CSV

## Recommended stack

| Layer | Choice | Why |
|---|---|---|
| App framework | **Streamlit** | Pure Python — reuses `matcher.py`, `judge.py`, `embedder.py`, `scrapers/`, `cv_extractor.py` almost unchanged. Built-in widgets for exactly what's needed: file uploader, text inputs, dataframe display, download button, progress spinners. No separate frontend codebase to build or maintain. |
| Hosting | **Streamlit Community Cloud** | Free tier, deploys directly from a GitHub branch (push → live URL, auto-redeploys on push), no server to manage. |
| Data storage (v1) | **None — session-only** | No database, no user accounts. Everything lives in `st.session_state` for the duration of the visit. Simplest possible correct starting point; a persistence layer is a later phase, not a blocker for launch. |
| API keys | **Bring-your-own-key (BYOK)**, entered in the UI per session | Avoids the site owner footing everyone's Voyage/Groq/Adzuna usage and avoids shared rate-limit contention (Voyage's free tier is capped at 3 req/min *per account* — sharing one key across every visitor would make the app unusably slow). Keys live only in that session's memory, never written to disk. |

### Alternatives considered

- **Gradio + Hugging Face Spaces** — similar tradeoffs to Streamlit, slightly better for single-function demos, slightly worse for a multi-step form-like flow (CV upload → key entry → config → results). Not chosen, but a reasonable fallback if Streamlit's theming ends up too limiting.
- **FastAPI backend + React/Next.js frontend (Vercel, free tier)** — most visually polished, most flexible, but roughly doubles engineering effort and requires maintaining two codebases in two languages. Recommended as a **phase 2** evolution once the Streamlit MVP validates that people actually want this, not as the starting point.

## Critical technical issue to fix first

Several modules currently read API keys as **module-level constants at import time**:

```python
# embedder.py, judge.py / groq_client.py, scrapers/adzuna.py — current pattern
API_KEY = os.environ.get("VOYAGE_API_KEY", "")
```

This is fine for a single-user local script (one process, one `.env`, one user). It is **not safe** for a hosted multi-user Streamlit app, where one Python process serves every visitor concurrently:
- A key read once at import time won't pick up a different user's key entered later in their session.
- Worse, if not handled carefully, one user's key could end up being used for another user's request.

**Fix:** refactor these modules so API keys are passed as explicit function parameters (or read from `st.session_state` at call time), not read once from `os.environ` at import time. This touches `embedder.py`, `groq_client.py`, `judge.py`, `scrapers/adzuna.py`, `scrapers/greenhouse_lever.py`, and `matcher.py`/`main.py`'s orchestration. This refactor is the prerequisite for everything else — do it before writing any UI code.

## Phases

**Phase 1 — Make the pipeline callable, not just runnable**
Refactor `main.py`'s logic out of a `if __name__ == "__main__"` script into an importable function, e.g. `run_pipeline(profile: dict, api_keys: dict, target_titles: list) -> pd.DataFrame`, with no reliance on `.env`, no global state, no `print()`-as-UI. Fix the import-time API key issue above as part of this. The existing CLI (`main.py`) becomes a thin wrapper around this function, so local usage keeps working unchanged.

**Phase 2 — Streamlit MVP**
- Page 1: CV upload (reuses `cv_extractor.py` + the Groq structuring call from `build_profile.py`) *or* a manual form as fallback, matching the existing `candidate_profile.example.json` schema.
- Page 2: API key inputs (Voyage, Groq, optionally Adzuna) with inline links to each provider's free signup, and a clear "these are used only for this session and never stored" note.
- Page 3: Run button → progress indicator per stage (scraping / embedding / judging) → results as an interactive, sortable table with the same columns as today's CSV, plus a "Download CSV" button.
- Deploy to Streamlit Community Cloud from this branch.

**Phase 3 — Polish**
- Custom theme (Streamlit supports a `config.toml` theme plus custom CSS injection) for a less "default Streamlit" look.
- Friendly error states: missing key → explain what's disabled instead of a stack trace; zero matches → explain the funnel instead of a blank page.
- Mobile-responsive check.

**Phase 4 — Optional, later: persistence**
If people want to return and see only *new* matches since their last visit (today's "new jobs only" dedup, currently per-machine via `output/seen_jobs.json`), that needs real accounts and a database — e.g. a free-tier Postgres (Supabase/Neon) keyed by a session token or lightweight login. Not needed for a v1 launch; stateless-per-visit is an acceptable and honest starting point.

## Open decisions (recommendations marked, but these are yours to confirm)

1. **BYOK vs. shared keys** — recommend BYOK (above). Shared keys mean you personally pay/rate-limit for every visitor.
2. **Persistence in v1** — recommend none (stateless). Adds real complexity (accounts, database) for a feature that's not needed to prove the concept.
3. **Keep the CLI tool alive alongside the web app** — recommend yes. The web app becomes an additive UI layer over the same core pipeline, not a replacement; your own daily-scheduled local run keeps working exactly as it does today.

## What's not changing

The scraping sources, scoring logic (5-facet weighting), embeddings, and LLM judge stay exactly as they are today — this plan is purely about *how the pipeline is invoked and how results are shown*, not about the matching logic itself.
