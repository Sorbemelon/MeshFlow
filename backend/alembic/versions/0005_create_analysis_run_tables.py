"""create analysis run tables

Revision ID: 0005_analysis_runs
Revises: 0004_create_dataset_transformation_tables
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0005_analysis_runs"
down_revision: str | None = "0004_transformations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("demo_session_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.String(length=512), nullable=False),
        sa.Column("normalized_question", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("intent", sa.String(length=128), nullable=True),
        sa.Column("source_model", sa.String(length=128), nullable=True),
        sa.Column("grain", sa.String(length=255), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("dimensions_json", sa.JSON(), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("output_schema_json", sa.JSON(), nullable=True),
        sa.Column("preview_rows_json", sa.JSON(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("failed_step", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("provider_chain_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_analysis_runs_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["demo_session_id"],
            ["demo_sessions.id"],
            name=op.f("fk_analysis_runs_demo_session_id_demo_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_runs")),
    )
    op.create_index(op.f("ix_analysis_runs_dataset_id"), "analysis_runs", ["dataset_id"])
    op.create_index(
        op.f("ix_analysis_runs_demo_session_id"),
        "analysis_runs",
        ["demo_session_id"],
    )
    op.create_index(
        op.f("ix_analysis_runs_normalized_question"),
        "analysis_runs",
        ["normalized_question"],
    )
    op.create_index(op.f("ix_analysis_runs_status"), "analysis_runs", ["status"])

    with op.batch_alter_table("ai_provider_runs") as batch_op:
        batch_op.add_column(sa.Column("analysis_run_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_ai_provider_runs_analysis_run_id_analysis_runs"),
            "analysis_runs",
            ["analysis_run_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            op.f("ix_ai_provider_runs_analysis_run_id"),
            ["analysis_run_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("ai_provider_runs") as batch_op:
        batch_op.drop_index(op.f("ix_ai_provider_runs_analysis_run_id"))
        batch_op.drop_constraint(
            op.f("fk_ai_provider_runs_analysis_run_id_analysis_runs"),
            type_="foreignkey",
        )
        batch_op.drop_column("analysis_run_id")
    op.drop_index(op.f("ix_analysis_runs_status"), table_name="analysis_runs")
    op.drop_index(
        op.f("ix_analysis_runs_normalized_question"),
        table_name="analysis_runs",
    )
    op.drop_index(op.f("ix_analysis_runs_demo_session_id"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_dataset_id"), table_name="analysis_runs")
    op.drop_table("analysis_runs")
