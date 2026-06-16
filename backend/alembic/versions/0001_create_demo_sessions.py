"""create demo sessions table

Revision ID: 0001_create_demo_sessions
Revises:
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001_create_demo_sessions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("successful_uploads_used", sa.Integer(), nullable=False),
        sa.Column("demo_dataset_used", sa.Integer(), nullable=False),
        sa.Column("uploaded_datasets_used", sa.Integer(), nullable=False),
        sa.Column("successful_analysis_runs_used", sa.Integer(), nullable=False),
        sa.Column("dashboard_cards_used", sa.Integer(), nullable=False),
        sa.Column("total_upload_mb_used", sa.Float(), nullable=False),
        sa.Column("created_from_ip_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_demo_sessions")),
    )
    op.create_index(op.f("ix_demo_sessions_status"), "demo_sessions", ["status"])
    op.create_index(op.f("ix_demo_sessions_expires_at"), "demo_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_demo_sessions_expires_at"), table_name="demo_sessions")
    op.drop_index(op.f("ix_demo_sessions_status"), table_name="demo_sessions")
    op.drop_table("demo_sessions")
