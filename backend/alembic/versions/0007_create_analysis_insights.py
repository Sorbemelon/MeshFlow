"""create analysis insights

Revision ID: 0007_insights
Revises: 0006_create_analysis_run_charts
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0007_insights"
down_revision: str | None = "0006_analysis_charts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_insights",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=64), nullable=False),
        sa.Column("analysis_run_chart_id", sa.String(length=64), nullable=True),
        sa.Column("insight_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=2048), nullable=True),
        sa.Column("key_findings_json", sa.JSON(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("provider_model", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_chart_id"],
            ["analysis_run_charts.id"],
            name=op.f("fk_analysis_insights_analysis_run_chart_id_analysis_run_charts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_analysis_insights_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_insights")),
    )
    op.create_index(
        op.f("ix_analysis_insights_analysis_run_chart_id"),
        "analysis_insights",
        ["analysis_run_chart_id"],
    )
    op.create_index(
        op.f("ix_analysis_insights_analysis_run_id"),
        "analysis_insights",
        ["analysis_run_id"],
    )
    op.create_index(
        op.f("ix_analysis_insights_insight_level"),
        "analysis_insights",
        ["insight_level"],
    )
    op.create_index(
        op.f("ix_analysis_insights_status"),
        "analysis_insights",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analysis_insights_status"), table_name="analysis_insights")
    op.drop_index(op.f("ix_analysis_insights_insight_level"), table_name="analysis_insights")
    op.drop_index(
        op.f("ix_analysis_insights_analysis_run_id"),
        table_name="analysis_insights",
    )
    op.drop_index(
        op.f("ix_analysis_insights_analysis_run_chart_id"),
        table_name="analysis_insights",
    )
    op.drop_table("analysis_insights")
