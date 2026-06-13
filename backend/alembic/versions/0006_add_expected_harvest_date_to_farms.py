"""add expected harvest date to farms

Revision ID: 0006_add_expected_harvest_date
Revises: 0005_create_recommendations
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_add_expected_harvest_date"
down_revision: str | None = "0005_create_recommendations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("farms", sa.Column("expected_harvest_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("farms", "expected_harvest_date")
