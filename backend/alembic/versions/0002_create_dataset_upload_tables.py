"""create dataset upload tables

Revision ID: 0002_create_dataset_upload_tables
Revises: 0001_create_demo_sessions
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_create_dataset_upload_tables"
down_revision: str | None = "0001_create_demo_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("demo_session_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("raw_table_name", sa.String(length=255), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["demo_session_id"],
            ["demo_sessions.id"],
            name=op.f("fk_datasets_demo_session_id_demo_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
    )
    op.create_index(op.f("ix_datasets_demo_session_id"), "datasets", ["demo_session_id"])
    op.create_index(op.f("ix_datasets_status"), "datasets", ["status"])

    op.create_table(
        "dataset_files",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dataset_files_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_files")),
    )
    op.create_index(op.f("ix_dataset_files_dataset_id"), "dataset_files", ["dataset_id"])

    op.create_table(
        "column_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_file_id", sa.String(length=64), nullable=True),
        sa.Column("column_index", sa.Integer(), nullable=False),
        sa.Column("raw_column_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_column_name", sa.String(length=255), nullable=False),
        sa.Column("snowflake_column_name", sa.String(length=255), nullable=False),
        sa.Column("detected_type", sa.String(length=32), nullable=False),
        sa.Column("null_count", sa.Integer(), nullable=False),
        sa.Column("null_rate", sa.Float(), nullable=False),
        sa.Column("unique_count", sa.Integer(), nullable=True),
        sa.Column("sample_values_json", sa.JSON(), nullable=False),
        sa.Column("parse_stats_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_file_id"],
            ["dataset_files.id"],
            name=op.f("fk_column_profiles_dataset_file_id_dataset_files"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_column_profiles_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_column_profiles")),
    )
    op.create_index(op.f("ix_column_profiles_dataset_id"), "column_profiles", ["dataset_id"])
    op.create_index(
        op.f("ix_column_profiles_dataset_file_id"),
        "column_profiles",
        ["dataset_file_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_column_profiles_dataset_file_id"), table_name="column_profiles")
    op.drop_index(op.f("ix_column_profiles_dataset_id"), table_name="column_profiles")
    op.drop_table("column_profiles")
    op.drop_index(op.f("ix_dataset_files_dataset_id"), table_name="dataset_files")
    op.drop_table("dataset_files")
    op.drop_index(op.f("ix_datasets_status"), table_name="datasets")
    op.drop_index(op.f("ix_datasets_demo_session_id"), table_name="datasets")
    op.drop_table("datasets")
