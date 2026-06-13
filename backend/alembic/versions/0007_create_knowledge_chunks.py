"""create knowledge chunks

Revision ID: 0007_create_knowledge_chunks
Revises: 0006_add_expected_harvest_date
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_create_knowledge_chunks"
down_revision: str | None = "0006_add_expected_harvest_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=220), nullable=False),
        sa.Column("source_name", sa.String(length=260), nullable=False),
        sa.Column("source_mime_type", sa.String(length=160), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("folder_id", sa.String(length=220), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("crop", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=160), nullable=True),
        sa.Column("topic", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "chunk_index", name="uq_knowledge_source_chunk"),
    )
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])
    op.create_index("ix_knowledge_chunks_folder_id", "knowledge_chunks", ["folder_id"])
    op.create_index("ix_knowledge_chunks_crop", "knowledge_chunks", ["crop"])
    op.create_index("ix_knowledge_chunks_region", "knowledge_chunks", ["region"])
    op.create_index("ix_knowledge_chunks_topic", "knowledge_chunks", ["topic"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_topic", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_region", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_crop", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_folder_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_source_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
