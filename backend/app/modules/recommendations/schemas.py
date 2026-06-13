from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendationAction(BaseModel):
    priority: int
    action: str
    reason: str
    evidence: list[str]


class RecommendationOutput(BaseModel):
    summary: str
    actions: list[RecommendationAction]


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    provider: str
    model: str | None
    prompt_version: str
    evidence_snapshot: dict
    output: RecommendationOutput
    created_at: datetime
