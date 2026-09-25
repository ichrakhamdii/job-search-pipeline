from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApplicationIn(BaseModel):
    job_fingerprint: str
    title: str
    company: str
    status: str = "saved"
    notes: str = ""


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class ApplicationOut(BaseModel):
    id: str
    job_fingerprint: str
    title: str
    company: str
    status: str
    notes: str
    applied_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
