# Web App Plan

Turn this from a locally-run CLI pipeline into a hosted web app: upload a CV, get a ranked job shortlist in the browser, no git clone, no Python setup, no terminal.

## Goal

Someone with zero coding background should be able to:
1. Open a URL
2. Upload their CV (or fill a short form)
3. Paste a couple of free API keys (with links to get them)
4. Click "Find Jobs"
5. See a ranked, sortable results table and download it as CSV
6. Pick a job and get a tailored CV + cover letter for it
7. Get mock interview questions and a technical test matching that job
8. Mark jobs as applied and track their status over time

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

**Phase 4 — Tailored CV & cover letter generator**

*What it does:* paste a job description (or click "Tailor for this job" on a shortlist row, which auto-fills the description already stored from scraping) → an LLM rewrites the CV's summary and re-emphasizes the most relevant experience/project bullets for that specific role, and drafts a matching cover letter grounded in the candidate's *actual* achievements — not generic filler.

*Tech:* same `groq_client.py` pattern as the judge stage — one new prompt + a Pydantic schema (`tailored_summary`, `emphasized_experience`, `cover_letter`). No new infrastructure.

*Output:* MVP renders as Markdown in the browser with a copy button. Polish pass exports as a formatted `.docx` (via `python-docx`, free/open-source) since a resume people actually send should look like a resume, not a wall of Markdown.

*Data flow:* input = the profile already in session + a job description (pasted or auto-filled). Stateless, on-demand — no persistence needed, same as the judge stage today.

*Honesty guardrail:* frame every output as a first draft to personalize further, not a ready-to-send final document — the same posture `build_profile.py` already takes with extracted profiles. An LLM cover letter grounded in real project details reads very differently from one built on vague prompts; the prompt needs to force specificity.

**Phase 5 — Mock interview questions & technical test generator**

*What it does:* paste or pick a job description → generates likely interview questions (behavioral + role-specific technical, based on what the posting actually asks for) plus a small technical exercise matching the JD's real tech stack, with hints at what a strong answer covers.

*Tech:* same pattern again — one more prompt + schema on the existing Groq call path.

*Scope guardrail:* this generates questions and guidance, not an auto-graded coding sandbox. Building real code execution/grading (e.g. via Judge0 or similar) is a materially different, much larger project — worth keeping explicitly out of scope unless there's real demand for it later.

*Data flow:* stateless, on-demand, identical shape to Phase 4. No persistence needed.

**Phase 6 — Application tracker**

*What it does:* mark a job (from the shortlist, or added manually) as Applied / Interviewing / Offer / Rejected, with a date and free-text notes, and see them all in one place on a later visit.

*Why this one is different:* Phases 4 and 5 are "generate something and show it" — nothing needs to be remembered after the tab closes. Tracking is inherently about remembering state *across visits*, which a stateless app cannot do. This is the feature that actually forces the persistence question the original Phase 4 (now renumbered) left optional.

*Two ways to build it, in order of how much I'd commit to up front:*

1. **(Recommended starting point) Local export/import file.** The tracker is just a CSV/JSON the user downloads after a session and re-uploads next time to pick up where they left off — the same pattern the app already uses for shortlist CSVs. Zero new infrastructure, zero accounts, consistent with the stateless philosophy chosen for v1. Real downside: manual file handling, easy to lose, no access from a second device without carrying the file around.
2. **(Real persistence — a genuine scope increase) Supabase free tier** (Postgres + built-in auth, generous free limits). Gives real accounts and cross-device access that survives forever, but adds authentication, a database schema, and ongoing account management to what has otherwise stayed a stateless tool. This is not a small add-on — it's the point where the project becomes a real multi-user service with accounts, not just a stateless calculator.

*Recommendation:* ship option 1 first. If people actually use tracking enough to feel the pain of manual file handling, that's the signal to invest in option 2 — not before.

**Phase 7 — Optional, later: real accounts + database**

If Phase 6 validates that people want tracking badly enough to justify it, this is where Supabase (or Neon/similar free-tier Postgres) gets introduced properly — and it can then *also* solve the original "remember new jobs since last visit" problem per-user, not just per-machine. One persistence layer, two features unlocked. Not needed for a v1 launch.

## Open decisions (recommendations marked, but these are yours to confirm)

1. **BYOK vs. shared keys** — recommend BYOK (above). Shared keys mean you personally pay/rate-limit for every visitor.
2. **Persistence in v1** — recommend none for the core pipeline, and the *local export/import* option (not a real database) for application tracking specifically. Real accounts are a deliberate later step, not a v1 requirement.
3. **Keep the CLI tool alive alongside the web app** — recommend yes. The web app becomes an additive UI layer over the same core pipeline, not a replacement; your own daily-scheduled local run keeps working exactly as it does today.
4. **How far to take the technical test generator** — recommend questions + guidance only, explicitly not an auto-graded execution sandbox, unless you decide later that's worth the added complexity.

## What's not changing

The scraping sources, scoring logic (5-facet weighting), embeddings, and LLM judge stay exactly as they are today — this plan is purely about *how the pipeline is invoked and how results are shown*, plus a few new on-demand generation features layered on top, not about the matching logic itself.
