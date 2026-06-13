from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.knowledge.chunking import content_hash
from app.modules.knowledge.models import KnowledgeChunk


class KnowledgeRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_source_chunks(
        self,
        source_id: str,
        source_name: str,
        source_mime_type: str | None,
        source_url: str | None,
        folder_id: str | None,
        chunks: list[str],
        metadata: dict[str, str | None],
    ) -> int:
        self.session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id))
        for index, chunk in enumerate(chunks):
            self.session.add(
                KnowledgeChunk(
                    source_id=source_id,
                    source_name=source_name,
                    source_mime_type=source_mime_type,
                    source_url=source_url,
                    folder_id=folder_id,
                    chunk_index=index,
                    text=chunk,
                    crop=metadata.get("crop"),
                    region=metadata.get("region"),
                    topic=metadata.get("topic"),
                    metadata_json=metadata,
                    content_hash=content_hash(chunk),
                )
            )
        self.session.commit()
        return len(chunks)

    def list_recent(self, limit: int = 50) -> list[KnowledgeChunk]:
        statement = select(KnowledgeChunk).order_by(KnowledgeChunk.updated_at.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def candidate_chunks(self, crop: str | None = None, limit: int = 200) -> list[KnowledgeChunk]:
        statement = select(KnowledgeChunk)
        if crop:
            statement = statement.where(
                (KnowledgeChunk.crop == crop.lower()) | (KnowledgeChunk.crop.is_(None))
            )
        statement = statement.order_by(KnowledgeChunk.updated_at.desc()).limit(limit)
        return list(self.session.scalars(statement).all())
