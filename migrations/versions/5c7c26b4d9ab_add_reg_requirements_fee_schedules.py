"""Add regulatory requirement and fee schedule tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from prep.models.guid import GUID


revision = "5c7c26b4d9ab"
down_revision = "b3f7f1a2e123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reg_fee_schedules",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("jurisdiction", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("paperwork", sa.JSON(), nullable=False),
        sa.Column("fees", sa.JSON(), nullable=False),
        sa.Column("totals", sa.JSON(), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "jurisdiction",
            "version",
            name="uq_reg_fee_schedule_jurisdiction_version",
        ),
    )
    op.create_index(
        "ix_reg_fee_schedules_jurisdiction",
        "reg_fee_schedules",
        ["jurisdiction"],
    )

    op.create_table(
        "reg_requirements",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("jurisdiction", sa.String(length=255), nullable=False),
        sa.Column("jurisdiction_kind", sa.String(length=50), nullable=False, server_default="city"),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="US"),
        sa.Column("state_code", sa.String(length=2), nullable=True),
        sa.Column("requirement_type", sa.String(length=100), nullable=False),
        sa.Column("normalized_type", sa.String(length=100), nullable=True),
        sa.Column("requirement_label", sa.String(length=255), nullable=False),
        sa.Column("governing_agency", sa.String(length=255), nullable=True),
        sa.Column("agency_type", sa.String(length=100), nullable=True),
        sa.Column("submission_channel", sa.String(length=100), nullable=True),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("inspection_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("renewal_frequency", sa.String(length=50), nullable=True),
        sa.Column("applies_to", sa.JSON(), nullable=False),
        sa.Column("required_documents", sa.JSON(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("fee_schedule_reference", sa.String(length=255), nullable=True),
        sa.Column("fee_amount_cents", sa.Integer(), nullable=True),
        sa.Column("fee_schedule_id", GUID(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["fee_schedule_id"],
            ["reg_fee_schedules.id"],
            name="fk_reg_requirements_fee_schedule",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("external_id", name="uq_reg_requirements_external_id"),
    )
    op.create_index(
        "ix_reg_requirements_jurisdiction",
        "reg_requirements",
        ["jurisdiction"],
    )
    op.create_index(
        "ix_reg_requirements_type",
        "reg_requirements",
        ["requirement_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_reg_requirements_type", table_name="reg_requirements")
    op.drop_index("ix_reg_requirements_jurisdiction", table_name="reg_requirements")
    op.drop_table("reg_requirements")

    op.drop_index("ix_reg_fee_schedules_jurisdiction", table_name="reg_fee_schedules")
    op.drop_table("reg_fee_schedules")
