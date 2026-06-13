from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSyncRequest(BaseModel):
    folder_ids: list[str] | None = None
    max_files: int | None = Field(default=None, ge=1, le=500)


class KnowledgeSyncResult(BaseModel):
    files_seen: int
    files_indexed: int
    chunks_indexed: int
    skipped_files: list[str]


class KnowledgeChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    source_name: str
    source_mime_type: str | None
    source_url: str | None
    folder_id: str | None
    chunk_index: int
    text: str
    crop: str | None
    region: str | None
    topic: str | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    crop: str | None = Field(default=None, max_length=120)
    limit: int = Field(default=6, ge=1, le=20)


class RetrievedKnowledge(BaseModel):
    source_name: str
    source_url: str | None
    crop: str | None
    topic: str | None
    text: str
    score: float
