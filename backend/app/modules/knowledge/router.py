from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.retrieval import tokenize
from app.modules.knowledge.schemas import (
    KnowledgeChunkRead,
    KnowledgeSearchRequest,
    KnowledgeSyncRequest,
    KnowledgeSyncResult,
    RetrievedKnowledge,
)
from app.modules.knowledge.service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(session: Session = Depends(get_session)) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(session))


@router.post("/sync", response_model=KnowledgeSyncResult)
def sync_knowledge(
    payload: KnowledgeSyncRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSyncResult:
    try:
        return service.sync_google_drive(
            folder_ids=payload.folder_ids,
            max_files=payload.max_files,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/chunks", response_model=list[KnowledgeChunkRead])
def list_chunks(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[KnowledgeChunkRead]:
    return KnowledgeRepository(session).list_recent(limit=limit)


@router.post("/search", response_model=list[RetrievedKnowledge])
def search_knowledge(
    payload: KnowledgeSearchRequest,
    session: Session = Depends(get_session),
) -> list[RetrievedKnowledge]:
    query_terms = tokenize(payload.query)
    chunks = KnowledgeRepository(session).candidate_chunks(crop=payload.crop, limit=250)
    scored = []
    for chunk in chunks:
        overlap = query_terms & tokenize(chunk.text)
        if overlap:
            score = float(len(overlap))
            if payload.crop and chunk.crop == payload.crop.lower():
                score += 3.0
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        RetrievedKnowledge(
            source_name=chunk.source_name,
            source_url=chunk.source_url,
            crop=chunk.crop,
            topic=chunk.topic,
            text=chunk.text[:1600],
            score=score,
        )
        for score, chunk in scored[: payload.limit]
    ]
