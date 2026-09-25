from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...deps import get_current_user
from ....core.database import get_db
from ....models.user import User
from ....schemas.application import ApplicationIn, ApplicationUpdate, ApplicationOut
from ....services import application_service

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationIn, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    return application_service.create_application(
        db, user.id, payload.job_fingerprint, payload.title, payload.company, payload.status, payload.notes,
    )


@router.get("", response_model=list[ApplicationOut])
def list_applications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return application_service.list_applications(db, user.id)


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(application_id: str, payload: ApplicationUpdate,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return application_service.update_application(db, user.id, application_id, payload.status, payload.notes)
