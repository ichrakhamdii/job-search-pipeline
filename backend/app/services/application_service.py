from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.application import Application


def create_application(db: Session, user_id: str, job_fingerprint: str, title: str,
                        company: str, status: str, notes: str) -> Application:
    app_row = Application(
        user_id=user_id,
        job_fingerprint=job_fingerprint,
        title=title,
        company=company,
        status=status,
        notes=notes,
        applied_at=datetime.now(timezone.utc) if status == "applied" else None,
    )
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return app_row


def list_applications(db: Session, user_id: str) -> list[Application]:
    return (db.query(Application)
              .filter(Application.user_id == user_id)
              .order_by(Application.updated_at.desc())
              .all())


def update_application(db: Session, user_id: str, application_id: str,
                        status: str | None, notes: str | None) -> Application:
    app_row = (db.query(Application)
                 .filter(Application.id == application_id, Application.user_id == user_id)
                 .first())
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")
    if status is not None:
        app_row.status = status
        if status == "applied" and not app_row.applied_at:
            app_row.applied_at = datetime.now(timezone.utc)
    if notes is not None:
        app_row.notes = notes
    db.commit()
    db.refresh(app_row)
    return app_row
