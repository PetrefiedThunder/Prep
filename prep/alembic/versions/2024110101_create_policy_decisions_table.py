"""create policy decisions table

Revision ID: c7f3d55fdb49
Revises: b47f1c1d5c4b
Create Date: 2024-11-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from prep.models.guid import GUID

# revision identifiers, used by Alembic.
revision = "c7f3d55fdb49"
down_revision = "b47f1c1d5c4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_decisions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=False),
        sa.Column("package_path", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.String(length=1024), nullable=True),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("triggered_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_decisions_request_hash", "policy_decisions", ["request_hash"], unique=False
    )
    op.create_index(
        "ix_policy_decisions_region_jurisdiction",
        "policy_decisions",
        ["region", "jurisdiction"],
        unique=False,
    )
    op.create_index(
        "ix_policy_decisions_decision_created",
        "policy_decisions",
        ["decision", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_policy_decisions_decision_created", table_name="policy_decisions")
    op.drop_index("ix_policy_decisions_region_jurisdiction", table_name="policy_decisions")
    op.drop_index("ix_policy_decisions_request_hash", table_name="policy_decisions")
    op.drop_table("policy_decisions")
