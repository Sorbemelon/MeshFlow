"""create semantic preparation tables

Revision ID: 0003_semantic_prep
Revises: 0002_create_dataset_upload_tables
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_semantic_prep"
down_revision: str | None = "0002_dataset_upload"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_columns",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("column_profile_id", sa.String(length=64), nullable=False),
        sa.Column("raw_column_name", sa.String(length=255), nullable=False),
        sa.Column("suggested_name", sa.String(length=128), nullable=False),
        sa.Column("semantic_role", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=False),
        sa.Column("approved_name", sa.String(length=128), nullable=True),
        sa.Column("approved_role", sa.String(length=32), nullable=True),
        sa.Column("include_in_model", sa.Boolean(), nullable=False),
        sa.Column("user_edited", sa.Boolean(), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("provider_model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["column_profile_id"],
            ["column_profiles.id"],
            name=op.f("fk_semantic_columns_column_profile_id_column_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_semantic_columns_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semantic_columns")),
    )
    op.create_index(
        op.f("ix_semantic_columns_column_profile_id"),
        "semantic_columns",
        ["column_profile_id"],
    )
    op.create_index(op.f("ix_semantic_columns_dataset_id"), "semantic_columns", ["dataset_id"])

    op.create_table(
        "dataset_question_suggestions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.String(length=255), nullable=False),
        sa.Column("intent", sa.String(length=128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("provider_model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dataset_question_suggestions_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_question_suggestions")),
    )
    op.create_index(
        op.f("ix_dataset_question_suggestions_dataset_id"),
        "dataset_question_suggestions",
        ["dataset_id"],
    )

    op.create_table(
        "ai_provider_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_model", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("fallback_from_provider", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_ai_provider_runs_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_provider_runs")),
    )
    op.create_index(op.f("ix_ai_provider_runs_dataset_id"), "ai_provider_runs", ["dataset_id"])
    op.create_index(op.f("ix_ai_provider_runs_status"), "ai_provider_runs", ["status"])
    op.create_index(op.f("ix_ai_provider_runs_task_type"), "ai_provider_runs", ["task_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_provider_runs_task_type"), table_name="ai_provider_runs")
    op.drop_index(op.f("ix_ai_provider_runs_status"), table_name="ai_provider_runs")
    op.drop_index(op.f("ix_ai_provider_runs_dataset_id"), table_name="ai_provider_runs")
    op.drop_table("ai_provider_runs")
    op.drop_index(
        op.f("ix_dataset_question_suggestions_dataset_id"),
        table_name="dataset_question_suggestions",
    )
    op.drop_table("dataset_question_suggestions")
    op.drop_index(op.f("ix_semantic_columns_dataset_id"), table_name="semantic_columns")
    op.drop_index(
        op.f("ix_semantic_columns_column_profile_id"),
        table_name="semantic_columns",
    )
    op.drop_table("semantic_columns")
