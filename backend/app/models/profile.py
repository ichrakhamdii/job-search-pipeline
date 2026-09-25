from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .util import gen_uuid, utcnow


class Profile(Base):
    """One row per user - the pipeline's candidate_profile.json, per-account instead of a file."""
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    location: Mapped[str] = mapped_column(String, default="")
    open_to_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    years_experience: Mapped[float] = mapped_column(Float, default=0)
    target_titles: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="profile")  # noqa: F821

    def to_pipeline_dict(self) -> dict:
        """Shape this row into exactly what pipeline.pipeline_service.run_pipeline() /
        pipeline.document_service expect - the same dict shape as candidate_profile.json.
        """
        return {
            "name": self.name,
            "email": self.email,
            "location": self.location,
            "open_to_remote": self.open_to_remote,
            "years_experience": self.years_experience,
            "target_titles": self.target_titles or [],
            "summary": self.summary,
            "skills": self.skills or [],
            "experience": self.experience or [],
            "projects": self.projects or [],
            "education": self.education or [],
            "certifications": self.certifications or [],
            "languages": self.languages or [],
        }
