"""create dashboard cards

Revision ID: 0008_create_dashboard_cards
Revises: 0007_create_analysis_insights
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0008_create_dashboard_cards"
down_revision: str | None = "0007_create_analysis_insights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_cards",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("demo_session_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=True),
        sa.Column("analysis_run_id", sa.String(length=64), nullable=True),
        sa.Column("analysis_run_chart_id", sa.String(length=64), nullable=True),
        sa.Column("card_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=512), nullable=True),
        sa.Column("dataset_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("source_model_snapshot", sa.String(length=128), nullable=True),
        sa.Column("card_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_chart_id"],
            ["analysis_run_charts.id"],
            name=op.f("fk_dashboard_cards_analysis_run_chart_id_analysis_run_charts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_dashboard_cards_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dashboard_cards_dataset_id_datasets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["demo_session_id"],
            ["demo_sessions.id"],
            name=op.f("fk_dashboard_cards_demo_session_id_demo_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dashboard_cards")),
    )
    op.create_index(op.f("ix_dashboard_cards_analysis_run_chart_id"), "dashboard_cards", ["analysis_run_chart_id"])
    op.create_index(op.f("ix_dashboard_cards_analysis_run_id"), "dashboard_cards", ["analysis_run_id"])
    op.create_index(op.f("ix_dashboard_cards_card_type"), "dashboard_cards", ["card_type"])
    op.create_index(op.f("ix_dashboard_cards_dataset_id"), "dashboard_cards", ["dataset_id"])
    op.create_index(op.f("ix_dashboard_cards_demo_session_id"), "dashboard_cards", ["demo_session_id"])
    op.create_index(op.f("ix_dashboard_cards_status"), "dashboard_cards", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_dashboard_cards_status"), table_name="dashboard_cards")
    op.drop_index(op.f("ix_dashboard_cards_demo_session_id"), table_name="dashboard_cards")
    op.drop_index(op.f("ix_dashboard_cards_dataset_id"), table_name="dashboard_cards")
    op.drop_index(op.f("ix_dashboard_cards_card_type"), table_name="dashboard_cards")
    op.drop_index(op.f("ix_dashboard_cards_analysis_run_id"), table_name="dashboard_cards")
    op.drop_index(op.f("ix_dashboard_cards_analysis_run_chart_id"), table_name="dashboard_cards")
    op.drop_table("dashboard_cards")
