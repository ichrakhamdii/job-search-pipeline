from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .util import gen_uuid, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False,  # noqa: F821
                                               cascade="all, delete-orphan")
    seen_jobs: Mapped[list["SeenJob"]] = relationship(back_populates="user",  # noqa: F821
                                                       cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user",  # noqa: F821
                                                              cascade="all, delete-orphan")
    documents: Mapped[list["GeneratedDocument"]] = relationship(back_populates="user",  # noqa: F821
                                                                 cascade="all, delete-orphan")
