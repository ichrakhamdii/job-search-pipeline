from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...deps import get_current_user
from ....core.database import get_db
from ....models.user import User
from ....schemas.document import DocumentRequest, DocumentOut
from ....services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/tailor-cv", response_model=DocumentOut, status_code=201)
def tailor_cv(payload: DocumentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return document_service.generate_tailored_cv(
        db, user.id, payload.job_description, payload.job_fingerprint, payload.groq_api_key,
    )


@router.post("/cover-letter", response_model=DocumentOut, status_code=201)
def cover_letter(payload: DocumentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return document_service.generate_cover_letter(
        db, user.id, payload.job_description, payload.job_fingerprint, payload.groq_api_key,
    )


@router.post("/mock-interview", response_model=DocumentOut, status_code=201)
def mock_interview(payload: DocumentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return document_service.generate_mock_interview(
        db, user.id, payload.job_description, payload.job_fingerprint, payload.groq_api_key,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return document_service.list_documents(db, user.id)
