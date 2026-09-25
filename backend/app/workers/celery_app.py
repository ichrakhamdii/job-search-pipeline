from celery import Celery

from ..core.config import settings

# Redis as both broker and result backend - Upstash's free tier works well here (serverless
# Redis, no local install needed, same "no local storage" reasoning as using Neon for Postgres).
celery_app = Celery("job_copilot", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Makes `celery -A app.workers.celery_app worker` discover tasks.py without an explicit import
# at the call site.
celery_app.autodiscover_tasks(["app.workers"])
