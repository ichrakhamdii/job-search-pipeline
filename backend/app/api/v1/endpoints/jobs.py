from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...deps import get_current_user
from ....core.database import get_db
from ....models.user import User
from ....models.job import SearchTask
from ....schemas.job import JobSearchRequest, JobResult, SearchTaskOut
from ....services import job_service
from ....workers.tasks import run_job_search_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/search", response_model=SearchTaskOut, status_code=202)
def start_search(payload: JobSearchRequest, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Kicks off the scrape -> score -> judge pipeline as a background Celery task and returns
    immediately with a task id to poll - a real run can take several minutes (rate-limited
    embedding/LLM calls), which would otherwise block this request or hit a timeout.
    """
    api_keys = payload.api_keys.model_dump()
    async_result = run_job_search_task.delay(user.id, api_keys, payload.extra_title)

    task_row = SearchTask(user_id=user.id, celery_task_id=async_result.id, status="pending")
    db.add(task_row)
    db.commit()
    db.refresh(task_row)
    return task_row


@router.get("/search/{task_id}", response_model=SearchTaskOut)
def get_search_status(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task_row = (db.query(SearchTask)
                  .filter(SearchTask.id == task_id, SearchTask.user_id == user.id)
                  .first())
    if not task_row:
        raise HTTPException(status_code=404, detail="Search task not found")
    return task_row


@router.get("/results", response_model=list[JobResult])
def get_results(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Past shortlist rows across all completed runs, most recent first."""
    return job_service.get_results(db, user.id)
