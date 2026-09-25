from datetime import datetime, timezone

from .celery_app import celery_app
from ..core.database import SessionLocal
from ..models.job import SearchTask
from ..services.job_service import run_search_for_user


@celery_app.task(bind=True)
def run_job_search_task(self, user_id: str, api_keys: dict, extra_title: str | None = None):
    """Runs the full scrape -> score -> judge pipeline in the background so the HTTP request
    that kicked it off doesn't block for however long rate-limited scraping/embedding/judging
    takes (observed several minutes for a real run with all sources active).

    Uses its own DB session (SessionLocal(), not the request-scoped get_db() dependency) since
    this executes in a separate Celery worker process, not inside a FastAPI request.
    """
    db = SessionLocal()
    task_row = db.query(SearchTask).filter(SearchTask.celery_task_id == self.request.id).first()
    try:
        if task_row:
            task_row.status = "running"
            db.commit()

        logs: list[str] = []
        ranked = run_search_for_user(db, user_id, api_keys, extra_title=extra_title, log=logs.append)

        if task_row:
            task_row.status = "succeeded"
            task_row.finished_at = datetime.now(timezone.utc)
            db.commit()

        return {"ranked_count": len(ranked), "logs": logs}
    except Exception as e:
        if task_row:
            task_row.status = "failed"
            task_row.error = str(e)
            task_row.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise
    finally:
        db.close()
