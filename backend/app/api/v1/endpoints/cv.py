from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from ...deps import get_current_user
from ....core.database import get_db
from ....models.user import User
from ....schemas.profile import ProfileIn, ProfileOut
from ....services import profile_service

router = APIRouter(prefix="/cv", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_service.get_profile(db, user.id)


@router.put("", response_model=ProfileOut)
def update_profile(payload: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_service.upsert_profile(db, user.id, payload.model_dump())


@router.post("/upload", response_model=ProfileOut)
async def upload_cv(
    groq_api_key: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extract text from an uploaded CV PDF and structure it into a profile via the LLM."""
    if not (file.content_type == "application/pdf" or (file.filename or "").lower().endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Only PDF files are supported right now.")
    contents = await file.read()
    return profile_service.build_profile_from_pdf_bytes(db, user.id, contents, groq_api_key)
