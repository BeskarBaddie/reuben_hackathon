"""add risk scores to analyses

Revision ID: 0004_add_risk_scores
Revises: 0003_add_climate_summary
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_risk_scores"
down_revision: str | None = "0003_add_climate_summary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("farm_analyses", sa.Column("drought_score", sa.Integer(), nullable=True))
    op.add_column("farm_analyses", sa.Column("drought_level", sa.String(length=40), nullable=True))
    op.add_column("farm_analyses", sa.Column("drought_drivers", sa.JSON(), nullable=True))
    op.add_column("farm_analyses", sa.Column("flood_score", sa.Integer(), nullable=True))
    op.add_column("farm_analyses", sa.Column("flood_level", sa.String(length=40), nullable=True))
    op.add_column("farm_analyses", sa.Column("flood_drivers", sa.JSON(), nullable=True))
    op.add_column("farm_analyses", sa.Column("heat_score", sa.Integer(), nullable=True))
    op.add_column("farm_analyses", sa.Column("heat_level", sa.String(length=40), nullable=True))
    op.add_column("farm_analyses", sa.Column("heat_drivers", sa.JSON(), nullable=True))
    op.add_column("farm_analyses", sa.Column("overall_risk_level", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("farm_analyses", "overall_risk_level")
    op.drop_column("farm_analyses", "heat_drivers")
    op.drop_column("farm_analyses", "heat_level")
    op.drop_column("farm_analyses", "heat_score")
    op.drop_column("farm_analyses", "flood_drivers")
    op.drop_column("farm_analyses", "flood_level")
    op.drop_column("farm_analyses", "flood_score")
    op.drop_column("farm_analyses", "drought_drivers")
    op.drop_column("farm_analyses", "drought_level")
    op.drop_column("farm_analyses", "drought_score")
