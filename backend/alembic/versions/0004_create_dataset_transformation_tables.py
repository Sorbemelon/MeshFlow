"""create dataset transformation tables

Revision ID: 0004_create_dataset_transformation_tables
Revises: 0003_create_semantic_preparation_tables
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004_create_dataset_transformation_tables"
down_revision: str | None = "0003_create_semantic_preparation_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_transformation_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_step", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("dbt_project_path", sa.String(length=1024), nullable=True),
        sa.Column("dbt_target_name", sa.String(length=64), nullable=True),
        sa.Column("dbt_run_summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dataset_transformation_runs_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_transformation_runs")),
    )
    op.create_index(
        op.f("ix_dataset_transformation_runs_dataset_id"),
        "dataset_transformation_runs",
        ["dataset_id"],
    )
    op.create_index(
        op.f("ix_dataset_transformation_runs_status"),
        "dataset_transformation_runs",
        ["status"],
    )

    op.create_table(
        "dbt_artifacts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("transformation_run_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("layer", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content_redacted", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dbt_artifacts_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transformation_run_id"],
            ["dataset_transformation_runs.id"],
            name=op.f("fk_dbt_artifacts_transformation_run_id_dataset_transformation_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dbt_artifacts")),
    )
    op.create_index(op.f("ix_dbt_artifacts_dataset_id"), "dbt_artifacts", ["dataset_id"])
    op.create_index(
        op.f("ix_dbt_artifacts_transformation_run_id"),
        "dbt_artifacts",
        ["transformation_run_id"],
    )

    op.create_table(
        "data_flow_nodes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("node_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_data_flow_nodes_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_flow_nodes")),
    )
    op.create_index(op.f("ix_data_flow_nodes_dataset_id"), "data_flow_nodes", ["dataset_id"])

    op.create_table(
        "data_flow_edges",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("from_node_id", sa.String(length=64), nullable=False),
        sa.Column("to_node_id", sa.String(length=64), nullable=False),
        sa.Column("edge_type", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_data_flow_edges_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_node_id"],
            ["data_flow_nodes.id"],
            name=op.f("fk_data_flow_edges_from_node_id_data_flow_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_node_id"],
            ["data_flow_nodes.id"],
            name=op.f("fk_data_flow_edges_to_node_id_data_flow_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_flow_edges")),
    )
    op.create_index(op.f("ix_data_flow_edges_dataset_id"), "data_flow_edges", ["dataset_id"])
    op.create_index(
        op.f("ix_data_flow_edges_from_node_id"),
        "data_flow_edges",
        ["from_node_id"],
    )
    op.create_index(
        op.f("ix_data_flow_edges_to_node_id"),
        "data_flow_edges",
        ["to_node_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_data_flow_edges_to_node_id"), table_name="data_flow_edges")
    op.drop_index(op.f("ix_data_flow_edges_from_node_id"), table_name="data_flow_edges")
    op.drop_index(op.f("ix_data_flow_edges_dataset_id"), table_name="data_flow_edges")
    op.drop_table("data_flow_edges")
    op.drop_index(op.f("ix_data_flow_nodes_dataset_id"), table_name="data_flow_nodes")
    op.drop_table("data_flow_nodes")
    op.drop_index(op.f("ix_dbt_artifacts_transformation_run_id"), table_name="dbt_artifacts")
    op.drop_index(op.f("ix_dbt_artifacts_dataset_id"), table_name="dbt_artifacts")
    op.drop_table("dbt_artifacts")
    op.drop_index(
        op.f("ix_dataset_transformation_runs_status"),
        table_name="dataset_transformation_runs",
    )
    op.drop_index(
        op.f("ix_dataset_transformation_runs_dataset_id"),
        table_name="dataset_transformation_runs",
    )
    op.drop_table("dataset_transformation_runs")
