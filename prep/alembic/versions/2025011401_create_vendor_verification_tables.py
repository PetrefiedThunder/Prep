"""create vendor verification tables

Revision ID: a8f5d2b1c9e3
Revises: c7f3d55fdb49
Create Date: 2025-01-14 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from prep.models.guid import GUID

# revision identifiers, used by Alembic.
revision = "a8f5d2b1c9e3"
down_revision = "c7f3d55fdb49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenants_api_key_hash", "tenants", ["api_key_hash"], unique=True)

    # Create vendors table
    op.create_table(
        "vendors",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("tenant_id", GUID(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("doing_business_as", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="onboarding"),
        sa.Column("primary_location", JSONB, nullable=False),
        sa.Column("contact", JSONB, nullable=True),
        sa.Column("tax_id_last4", sa.String(length=4), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_vendor_tenant_external"),
    )
    op.create_index("ix_vendors_tenant_id", "vendors", ["tenant_id"])
    op.create_index("ix_vendors_status", "vendors", ["status"])

    # Create vendor_documents table
    op.create_table(
        "vendor_documents",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("vendor_id", GUID(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("jurisdiction", JSONB, nullable=False),
        sa.Column("expires_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendor_documents_vendor_id", "vendor_documents", ["vendor_id"])
    op.create_index("ix_vendor_documents_type", "vendor_documents", ["type"])

    # Create verification_runs table
    op.create_table(
        "verification_runs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("tenant_id", GUID(), nullable=False),
        sa.Column("vendor_id", GUID(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending_documents"
        ),
        sa.Column("jurisdiction", JSONB, nullable=False),
        sa.Column("kitchen_id", sa.String(length=255), nullable=True),
        sa.Column("initiated_by", sa.String(length=255), nullable=True),
        sa.Column("initiated_from", sa.String(length=50), nullable=False, server_default="api"),
        sa.Column("ruleset_name", sa.String(length=255), nullable=False),
        sa.Column("regulation_version", sa.String(length=100), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("decision_snapshot", JSONB, nullable=True),
        sa.Column("inputs_hash", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_runs_tenant_id", "verification_runs", ["tenant_id"])
    op.create_index("ix_verification_runs_vendor_id", "verification_runs", ["vendor_id"])
    op.create_index("ix_verification_runs_status", "verification_runs", ["status"])
    op.create_index("ix_verification_runs_inputs_hash", "verification_runs", ["inputs_hash"])
    op.create_index(
        "ix_verification_runs_idempotency_key", "verification_runs", ["idempotency_key"]
    )

    # Create audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("tenant_id", GUID(), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("audit_events")
    op.drop_table("verification_runs")
    op.drop_table("vendor_documents")
    op.drop_table("vendors")
    op.drop_table("tenants")
