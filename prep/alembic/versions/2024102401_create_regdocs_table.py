"""create regdocs table

Revision ID: 9b4fe8edcf5d
Revises:
Create Date: 2024-10-24 00:00:00.000000
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path to allow imports
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import sqlalchemy as sa
from alembic import op

from prep.models.guid import GUID

# revision identifiers, used by Alembic.
revision = "9b4fe8edcf5d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regdocs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("doc_type", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256_hash", name="uq_regdocs_sha256_hash"),
    )
    op.create_index("ix_regdocs_sha256_hash", "regdocs", ["sha256_hash"], unique=False)
    op.create_index("ix_regdocs_jurisdiction", "regdocs", ["jurisdiction"], unique=False)
    op.create_index(
        "ix_regdocs_state_doc_type",
        "regdocs",
        ["state", "doc_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_regdocs_state_doc_type", table_name="regdocs")
    op.drop_index("ix_regdocs_jurisdiction", table_name="regdocs")
    op.drop_index("ix_regdocs_sha256_hash", table_name="regdocs")
    op.drop_table("regdocs")
