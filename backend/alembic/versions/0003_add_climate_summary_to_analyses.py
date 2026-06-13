"""add climate summary to analyses

Revision ID: 0003_add_climate_summary
Revises: 0002_create_farm_analyses
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_climate_summary"
down_revision: str | None = "0002_create_farm_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("farm_analyses", sa.Column("climate_season_start", sa.String(length=32), nullable=True))
    op.add_column("farm_analyses", sa.Column("climate_season_end", sa.String(length=32), nullable=True))
    op.add_column("farm_analyses", sa.Column("rainfall_this_season_mm", sa.Float(), nullable=True))
    op.add_column("farm_analyses", sa.Column("rainfall_historical_average_mm", sa.Float(), nullable=True))
    op.add_column("farm_analyses", sa.Column("rainfall_anomaly_percent", sa.Float(), nullable=True))
    op.add_column("farm_analyses", sa.Column("temperature_this_season_c", sa.Float(), nullable=True))
    op.add_column("farm_analyses", sa.Column("temperature_historical_average_c", sa.Float(), nullable=True))
    op.add_column("farm_analyses", sa.Column("temperature_anomaly_c", sa.Float(), nullable=True))
    op.add_column("farm_analyses", sa.Column("climate_signal", sa.String(length=120), nullable=True))
    op.add_column("farm_analyses", sa.Column("climate_source", sa.String(length=220), nullable=True))
    op.add_column("farm_analyses", sa.Column("climate_evidence", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("farm_analyses", "climate_evidence")
    op.drop_column("farm_analyses", "climate_source")
    op.drop_column("farm_analyses", "climate_signal")
    op.drop_column("farm_analyses", "temperature_anomaly_c")
    op.drop_column("farm_analyses", "temperature_historical_average_c")
    op.drop_column("farm_analyses", "temperature_this_season_c")
    op.drop_column("farm_analyses", "rainfall_anomaly_percent")
    op.drop_column("farm_analyses", "rainfall_historical_average_mm")
    op.drop_column("farm_analyses", "rainfall_this_season_mm")
    op.drop_column("farm_analyses", "climate_season_end")
    op.drop_column("farm_analyses", "climate_season_start")
