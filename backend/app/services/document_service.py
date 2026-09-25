from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.document import GeneratedDocument
from ..models.profile import Profile


def _get_profile_dict(db: Session, user_id: str) -> dict:
    profile_row = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile_row:
        raise HTTPException(status_code=400, detail="Create a profile first")
    return profile_row.to_pipeline_dict()


def _generate_and_save(db: Session, user_id: str, doc_type: str, job_fingerprint: str,
                        content: str) -> GeneratedDocument:
    doc = GeneratedDocument(user_id=user_id, job_fingerprint=job_fingerprint or "",
                             type=doc_type, content=content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def generate_tailored_cv(db: Session, user_id: str, job_description: str,
                          job_fingerprint: str | None, groq_api_key: str | None) -> GeneratedDocument:
    from pipeline.document_service import tailor_cv

    profile = _get_profile_dict(db, user_id)
    try:
        content = tailor_cv(profile, job_description, api_key=groq_api_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _generate_and_save(db, user_id, "tailored_cv", job_fingerprint, content)


def generate_cover_letter(db: Session, user_id: str, job_description: str,
                           job_fingerprint: str | None, groq_api_key: str | None) -> GeneratedDocument:
    from pipeline.document_service import cover_letter

    profile = _get_profile_dict(db, user_id)
    try:
        content = cover_letter(profile, job_description, api_key=groq_api_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _generate_and_save(db, user_id, "cover_letter", job_fingerprint, content)


def generate_mock_interview(db: Session, user_id: str, job_description: str,
                             job_fingerprint: str | None, groq_api_key: str | None) -> GeneratedDocument:
    from pipeline.document_service import mock_interview

    profile = _get_profile_dict(db, user_id)
    try:
        content = mock_interview(profile, job_description, api_key=groq_api_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _generate_and_save(db, user_id, "interview_prep", job_fingerprint, content)


def list_documents(db: Session, user_id: str) -> list[GeneratedDocument]:
    return (db.query(GeneratedDocument)
              .filter(GeneratedDocument.user_id == user_id)
              .order_by(GeneratedDocument.created_at.desc())
              .all())
