"""Add postal_code and county columns to kitchens table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b47f1c1d5c4b"
down_revision = "9b4fe8edcf5d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kitchens", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("kitchens", sa.Column("county", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("kitchens", "county")
    op.drop_column("kitchens", "postal_code")
