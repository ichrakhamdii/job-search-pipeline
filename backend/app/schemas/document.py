from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentRequest(BaseModel):
    job_description: str
    job_fingerprint: Optional[str] = None
    groq_api_key: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    type: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
