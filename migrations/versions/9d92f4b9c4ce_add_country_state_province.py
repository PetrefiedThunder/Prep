"""Add country and state/province fields to regulatory tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9d92f4b9c4ce"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "regulation_sources",
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="US"),
    )
    op.add_column(
        "regulation_sources",
        sa.Column("state_province", sa.String(length=100), nullable=True),
    )
    op.execute(
        "UPDATE regulation_sources SET state_province = state "
        "WHERE state_province IS NULL AND state IS NOT NULL"
    )
    op.alter_column(
        "regulation_sources",
        "country_code",
        server_default=None,
        existing_type=sa.String(length=2),
    )

    op.add_column(
        "regulations",
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="US"),
    )
    op.add_column(
        "regulations",
        sa.Column("state_province", sa.String(length=100), nullable=True),
    )
    op.execute(
        "UPDATE regulations SET state_province = upper(jurisdiction) "
        "WHERE state_province IS NULL AND char_length(jurisdiction) = 2"
    )
    op.alter_column(
        "regulations",
        "country_code",
        server_default=None,
        existing_type=sa.String(length=2),
    )

    op.add_column(
        "insurance_requirements",
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="US"),
    )
    op.add_column(
        "insurance_requirements",
        sa.Column("state_province", sa.String(length=100), nullable=True),
    )
    op.execute(
        "UPDATE insurance_requirements SET state_province = state "
        "WHERE state_province IS NULL AND state IS NOT NULL"
    )
    op.alter_column(
        "insurance_requirements",
        "country_code",
        server_default=None,
        existing_type=sa.String(length=2),
    )

    op.add_column(
        "regdocs",
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="US"),
    )
    op.add_column(
        "regdocs",
        sa.Column("state_province", sa.String(length=120), nullable=True),
    )
    op.execute(
        "UPDATE regdocs SET state_province = state "
        "WHERE state_province IS NULL AND state IS NOT NULL"
    )
    op.alter_column(
        "regdocs",
        "country_code",
        server_default=None,
        existing_type=sa.String(length=2),
    )


def downgrade() -> None:
    op.drop_column("regdocs", "state_province")
    op.drop_column("regdocs", "country_code")

    op.drop_column("insurance_requirements", "state_province")
    op.drop_column("insurance_requirements", "country_code")

    op.drop_column("regulations", "state_province")
    op.drop_column("regulations", "country_code")

    op.drop_column("regulation_sources", "state_province")
    op.drop_column("regulation_sources", "country_code")
