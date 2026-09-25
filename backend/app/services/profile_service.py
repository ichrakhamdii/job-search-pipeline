from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.profile import Profile

PROFILE_FIELDS = ["name", "email", "location", "open_to_remote", "years_experience",
                   "target_titles", "summary", "skills", "experience", "projects",
                   "education", "certifications", "languages"]


def upsert_profile(db: Session, user_id: str, data: dict) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
    for field in PROFILE_FIELDS:
        if field in data:
            setattr(profile, field, data[field])
    db.commit()
    db.refresh(profile)
    return profile


def get_profile(db: Session, user_id: str) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile yet - upload a CV or PUT one")
    return profile


def build_profile_from_pdf_bytes(db: Session, user_id: str, pdf_bytes: bytes, groq_api_key: str) -> Profile:
    """Extracts text from an uploaded CV PDF and structures it via the LLM - the exact same
    pipeline.cv_extractor + pipeline.profile_builder logic the CLI's build_profile.py uses,
    reused here as a library instead of duplicated.
    """
    import tempfile
    from pipeline.cv_extractor import extract_text
    from pipeline.profile_builder import build_profile_from_cv

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        try:
            cv_text = extract_text(tmp.name)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not extract text from PDF: {e}")

    try:
        profile_data = build_profile_from_cv(cv_text, api_key=groq_api_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CV extraction failed: {e}")

    return upsert_profile(db, user_id, profile_data)
