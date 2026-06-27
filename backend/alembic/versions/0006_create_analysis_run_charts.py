"""create analysis run charts

Revision ID: 0006_analysis_charts
Revises: 0005_create_analysis_run_tables
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0006_analysis_charts"
down_revision: str | None = "0005_analysis_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_run_charts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("chart_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("chart_spec_json", sa.JSON(), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("source_model", sa.String(length=128), nullable=True),
        sa.Column("metric_summary", sa.String(length=255), nullable=True),
        sa.Column("dimension_summary", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_analysis_run_charts_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_analysis_run_charts_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_run_charts")),
    )
    op.create_index(
        op.f("ix_analysis_run_charts_analysis_run_id"),
        "analysis_run_charts",
        ["analysis_run_id"],
    )
    op.create_index(
        op.f("ix_analysis_run_charts_chart_type"),
        "analysis_run_charts",
        ["chart_type"],
    )
    op.create_index(
        op.f("ix_analysis_run_charts_dataset_id"),
        "analysis_run_charts",
        ["dataset_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analysis_run_charts_dataset_id"), table_name="analysis_run_charts")
    op.drop_index(op.f("ix_analysis_run_charts_chart_type"), table_name="analysis_run_charts")
    op.drop_index(
        op.f("ix_analysis_run_charts_analysis_run_id"),
        table_name="analysis_run_charts",
    )
    op.drop_table("analysis_run_charts")
