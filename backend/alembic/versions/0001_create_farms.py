"""create farms

Revision ID: 0001_create_farms
Revises:
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_farms"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    irrigation_type = sa.Enum("none", "rainfed", "partial", "full", name="irrigation_type")
    irrigation_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "farms",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("crop", sa.String(length=120), nullable=False),
        sa.Column("planting_date", sa.Date(), nullable=True),
        sa.Column("irrigation_type", irrigation_type, nullable=False),
        sa.Column("area_hectares", sa.Float(), nullable=False),
        sa.Column(
            "boundary",
            geoalchemy2.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farms_owner_id", "farms", ["owner_id"])
    op.create_index("idx_farms_boundary", "farms", ["boundary"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("idx_farms_boundary", table_name="farms", postgresql_using="gist")
    op.drop_index("ix_farms_owner_id", table_name="farms")
    op.drop_table("farms")
    sa.Enum(name="irrigation_type").drop(op.get_bind(), checkfirst=True)
