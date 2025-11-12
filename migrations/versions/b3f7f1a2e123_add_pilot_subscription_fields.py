"""Add pilot metadata and subscription tracking."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b3f7f1a2e123"
down_revision = "1f3d6a5b2c4e"
branch_labels = None
depends_on = None


_SUBSCRIPTION_STATUS_ENUM = postgresql.ENUM(
    "inactive", "trial", "active", "canceled", name="subscriptionstatus"
)


def upgrade() -> None:
    bind = op.get_bind()
    _SUBSCRIPTION_STATUS_ENUM.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column("is_pilot_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("pilot_county", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("pilot_zip_code", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_status",
            _SUBSCRIPTION_STATUS_ENUM,
            nullable=False,
            server_default="inactive",
        ),
    )
    op.add_column(
        "users",
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.alter_column("users", "is_pilot_user", server_default=None)
    op.alter_column("users", "subscription_status", server_default=None)

    op.create_table(
        "api_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_usage_user_id", "api_usage", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_usage_user_id", table_name="api_usage")
    op.drop_table("api_usage")

    op.drop_column("users", "trial_ends_at")
    op.drop_column("users", "trial_started_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "pilot_zip_code")
    op.drop_column("users", "pilot_county")
    op.drop_column("users", "is_pilot_user")

    _SUBSCRIPTION_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
