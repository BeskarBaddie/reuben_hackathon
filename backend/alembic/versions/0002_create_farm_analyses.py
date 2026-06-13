"""create farm analyses

Revision ID: 0002_create_farm_analyses
Revises: 0001_create_farms
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_create_farm_analyses"
down_revision: str | None = "0001_create_farms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    analysis_status = sa.Enum("queued", "processing", "completed", "failed", name="analysis_status")
    analysis_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "farm_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("farm_id", sa.UUID(), nullable=False),
        sa.Column("status", analysis_status, nullable=False),
        sa.Column("ndvi", sa.Float(), nullable=True),
        sa.Column("vegetation_health", sa.String(length=80), nullable=True),
        sa.Column("vegetation_trend", sa.String(length=80), nullable=True),
        sa.Column("water_stress", sa.String(length=80), nullable=True),
        sa.Column("image_date", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=160), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farm_analyses_farm_id", "farm_analyses", ["farm_id"])


def downgrade() -> None:
    op.drop_index("ix_farm_analyses_farm_id", table_name="farm_analyses")
    op.drop_table("farm_analyses")
    sa.Enum(name="analysis_status").drop(op.get_bind(), checkfirst=True)
