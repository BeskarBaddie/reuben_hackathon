from app.core.config import settings
from app.modules.knowledge.chunking import chunk_text, infer_metadata
from app.modules.knowledge.drive_client import GoogleDriveKnowledgeClient
from app.modules.knowledge.parsers import parse_document_bytes
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import KnowledgeSyncResult


class KnowledgeService:
    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    def sync_google_drive(
        self,
        folder_ids: list[str] | None = None,
        max_files: int | None = None,
    ) -> KnowledgeSyncResult:
        folders = folder_ids or settings.google_drive_folder_ids
        if not folders:
            raise RuntimeError("No Google Drive folder IDs configured")

        client = GoogleDriveKnowledgeClient()
        files = client.list_files(folder_ids=folders, max_files=max_files)
        files_indexed = 0
        chunks_indexed = 0
        skipped_files: list[str] = []

        for file in files:
            try:
                content = client.download_file(file)
                parsed = parse_document_bytes(content, file.mime_type, file.name)
            except Exception as exc:
                skipped_files.append(f"{file.name}: {exc}")
                continue

            if parsed.skipped_reason:
                skipped_files.append(f"{file.name}: {parsed.skipped_reason}")
                continue

            chunks = chunk_text(parsed.text)
            if not chunks:
                skipped_files.append(f"{file.name}: no extractable text")
                continue

            metadata = infer_metadata(file.name, parsed.text)
            count = self.repository.replace_source_chunks(
                source_id=file.id,
                source_name=file.name,
                source_mime_type=file.mime_type,
                source_url=file.web_view_link,
                folder_id=file.folder_id,
                chunks=chunks,
                metadata=metadata,
            )
            files_indexed += 1
            chunks_indexed += count

        return KnowledgeSyncResult(
            files_seen=len(files),
            files_indexed=files_indexed,
            chunks_indexed=chunks_indexed,
            skipped_files=skipped_files,
        )
