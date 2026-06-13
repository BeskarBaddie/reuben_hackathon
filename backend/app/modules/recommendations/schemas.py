from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActionGrounding(BaseModel):
    grounded: bool
    score: float
    source: str | None = None
    title: str | None = None
    path: str | None = None
    page: int | None = None


class RecommendationAction(BaseModel):
    priority: int
    action: str
    steps: list[str] = []
    reason: str
    evidence: list[str]
    grounding: ActionGrounding | None = None


class RecommendationCitation(BaseModel):
    doc_id: str
    title: str
    source: str
    path: str = ""
    page: int = 0


class RecommendationOutput(BaseModel):
    summary: str
    narrative: str
    forecast_summary: str
    actions: list[RecommendationAction]
    citations: list[RecommendationCitation] = []


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
