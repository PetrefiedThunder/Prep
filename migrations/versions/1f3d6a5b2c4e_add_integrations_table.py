"""Add integrations table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1f3d6a5b2c4e"
down_revision = "9d92f4b9c4ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_type", sa.String(length=120), nullable=False),
        sa.Column("vendor_name", sa.String(length=120), nullable=False),
        sa.Column("auth_method", sa.String(length=50), nullable=False),
        sa.Column("sync_frequency", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_integrations_user_id", "integrations", ["user_id"])
    op.create_index("ix_integrations_kitchen_id", "integrations", ["kitchen_id"])


def downgrade() -> None:
    op.drop_index("ix_integrations_kitchen_id", table_name="integrations")
    op.drop_index("ix_integrations_user_id", table_name="integrations")
    op.drop_table("integrations")
