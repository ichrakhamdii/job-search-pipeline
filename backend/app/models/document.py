from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .util import gen_uuid, utcnow


class GeneratedDocument(Base):
    """Tailored CVs, cover letters, and interview prep - kept so past generations aren't lost."""
    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    job_fingerprint: Mapped[str] = mapped_column(String, default="")
    type: Mapped[str] = mapped_column(String, nullable=False)  # tailored_cv/cover_letter/interview_prep
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
