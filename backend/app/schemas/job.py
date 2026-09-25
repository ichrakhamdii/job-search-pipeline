from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApiKeysIn(BaseModel):
    """BYOK: every field optional, each missing key just degrades that stage gracefully."""
    voyage_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    adzuna_app_id: Optional[str] = None
    adzuna_app_key: Optional[str] = None
    greenhouse_companies: list[str] = []
    lever_companies: list[str] = []


class JobSearchRequest(BaseModel):
    api_keys: ApiKeysIn
    extra_title: Optional[str] = None


class JobResult(BaseModel):
    match_score: float
    title: str
    company: str
    location: str = ""
    source: str = ""
    url: str = ""
    description: str = ""
    llm_recommendation: str = ""
    llm_rationale: str = ""
    international_signals: str = ""

    model_config = ConfigDict(extra="allow")


class SearchTaskOut(BaseModel):
    id: str
    status: str
    error: str = ""
    created_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
