from sqlalchemy.orm import Session

from ..models.job import SeenJob, ShortlistResult
from ..models.profile import Profile


def run_search_for_user(db: Session, user_id: str, api_keys: dict, extra_title: str | None = None,
                         top_n: int = 50, log=print) -> list[dict]:
    """Runs the shared scrape -> score -> judge pipeline for one user and persists results.

    Deliberately raises plain ValueError (not HTTPException) - this function is called from
    both the synchronous endpoint and the Celery worker task, neither of which should force
    the other to depend on FastAPI's exception types.
    """
    from pipeline.pipeline_service import run_pipeline, job_fingerprint

    profile_row = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile_row:
        raise ValueError("No profile found for this user - create one first.")

    profile = profile_row.to_pipeline_dict()
    titles = list(profile.get("target_titles", []))
    if extra_title:
        titles.append(extra_title)
    if not titles:
        titles = [""]

    seen_rows = db.query(SeenJob).filter(SeenJob.user_id == user_id).all()
    existing_fingerprints = {row.job_fingerprint for row in seen_rows}
    seen = {row.job_fingerprint: {"title": row.title, "company": row.company} for row in seen_rows}

    ranked = run_pipeline(profile, titles, seen, api_keys, top_n=top_n, log=log)

    # `seen` was mutated in place with every fingerprint encountered this run.
    for fp, meta in seen.items():
        if fp not in existing_fingerprints:
            db.add(SeenJob(user_id=user_id, job_fingerprint=fp,
                            title=meta.get("title", ""), company=meta.get("company", "")))

    for job in ranked:
        db.add(ShortlistResult(
            user_id=user_id,
            job_fingerprint=job_fingerprint(job),
            title=job.get("title", ""),
            company=job.get("company", ""),
            data=job,
        ))
    db.commit()

    return ranked


def get_results(db: Session, user_id: str, limit: int = 200) -> list[dict]:
    """Past shortlist rows across all runs, most recent first."""
    rows = (db.query(ShortlistResult)
              .filter(ShortlistResult.user_id == user_id)
              .order_by(ShortlistResult.run_at.desc())
              .limit(limit)
              .all())
    return [row.data for row in rows]
