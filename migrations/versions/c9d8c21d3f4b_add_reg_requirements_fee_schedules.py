"""Add fee schedule and regulatory requirement tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from prep.models.guid import GUID

revision = "c9d8c21d3f4b"
down_revision = "b3f7f1a2e123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fee_schedules",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("paperwork", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("fees", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("effective_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("jurisdiction", name="uq_fee_schedules_jurisdiction"),
    )
    op.create_index(
        "ix_fee_schedules_jurisdiction",
        "fee_schedules",
        ["jurisdiction"],
    )

    op.create_table(
        "reg_requirements",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "requirement_type",
            sa.String(length=100),
            nullable=False,
            server_default="general",
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("documents", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("applies_to", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("fee_schedule_id", GUID(), nullable=True),
        sa.ForeignKeyConstraint(["fee_schedule_id"], ["fee_schedules.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "jurisdiction",
            "external_id",
            name="uq_reg_requirements_jurisdiction_external",
        ),
    )
    op.create_index(
        "ix_reg_requirements_jurisdiction",
        "reg_requirements",
        ["jurisdiction"],
    )
    op.create_index(
        "ix_reg_requirements_requirement_type",
        "reg_requirements",
        ["requirement_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_reg_requirements_requirement_type", table_name="reg_requirements")
    op.drop_index("ix_reg_requirements_jurisdiction", table_name="reg_requirements")
    op.drop_table("reg_requirements")
    op.drop_index("ix_fee_schedules_jurisdiction", table_name="fee_schedules")
    op.drop_table("fee_schedules")
