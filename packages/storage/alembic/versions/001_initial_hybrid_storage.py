"""Initial hybrid storage tables (D011).

Revision ID: 001_initial
Revises:
Create Date: 2026-07-21

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "input_packages",
        sa.Column("package_id", sa.String(length=128), primary_key=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "raw_sources",
        sa.Column("source_id", sa.String(length=128), primary_key=True),
        sa.Column("input_package_id", sa.String(length=128), nullable=True),
        sa.Column("content_digest", sa.String(length=128), nullable=True),
        sa.Column("storage_location", sa.Text(), nullable=True),
        sa.Column("manuscript_id", sa.String(length=128), nullable=True),
        sa.Column("version_id", sa.String(length=128), nullable=True),
        sa.Column("parent_version_ids", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_raw_sources_content_digest", "raw_sources", ["content_digest"])
    op.create_index("ix_raw_sources_manuscript_id", "raw_sources", ["manuscript_id"])

    op.create_table(
        "manuscript_versions",
        sa.Column("version_id", sa.String(length=128), primary_key=True),
        sa.Column("manuscript_id", sa.String(length=128), nullable=False),
        sa.Column("content_digest", sa.String(length=128), nullable=False),
        sa.Column("parent_version_ids", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_manuscript_versions_manuscript_id", "manuscript_versions", ["manuscript_id"])
    op.create_index("ix_manuscript_versions_content_digest", "manuscript_versions", ["content_digest"])

    op.create_table(
        "work_plans",
        sa.Column("plan_id", sa.String(length=128), primary_key=True),
        sa.Column("manuscript_id", sa.String(length=128), nullable=True),
        sa.Column("version_id", sa.String(length=128), nullable=True),
        sa.Column("content_digest", sa.String(length=128), nullable=True),
        sa.Column("parent_version_ids", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_work_plans_manuscript_id", "work_plans", ["manuscript_id"])

    op.create_table(
        "revision_decisions",
        sa.Column("decision_id", sa.String(length=128), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("manuscript_id", sa.String(length=128), nullable=True),
        sa.Column("version_id", sa.String(length=128), nullable=True),
        sa.Column("content_digest", sa.String(length=128), nullable=True),
        sa.Column("parent_version_ids", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_revision_decisions_run_id", "revision_decisions", ["run_id"])
    op.create_index("ix_revision_decisions_manuscript_id", "revision_decisions", ["manuscript_id"])

    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=128), primary_key=True),
        sa.Column("manuscript_id", sa.String(length=128), nullable=True),
        sa.Column("version_id", sa.String(length=128), nullable=True),
        sa.Column("content_digest", sa.String(length=128), nullable=True),
        sa.Column("parent_version_ids", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_runs_manuscript_id", "runs", ["manuscript_id"])


def downgrade() -> None:
    op.drop_table("runs")
    op.drop_table("revision_decisions")
    op.drop_table("work_plans")
    op.drop_table("manuscript_versions")
    op.drop_table("raw_sources")
    op.drop_table("input_packages")
