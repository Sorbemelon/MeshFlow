from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_dataset_id() -> str:
    return f"ds_{uuid4().hex}"


def generate_dataset_file_id() -> str:
    return f"file_{uuid4().hex}"


def generate_column_profile_id() -> str:
    return f"col_{uuid4().hex}"


def generate_semantic_column_id() -> str:
    return f"sem_col_{uuid4().hex}"


def generate_question_suggestion_id() -> str:
    return f"qst_{uuid4().hex}"


def generate_provider_run_id() -> str:
    return f"ai_run_{uuid4().hex}"


def generate_analysis_run_id() -> str:
    return f"an_run_{uuid4().hex}"


def generate_analysis_run_chart_id() -> str:
    return f"an_chart_{uuid4().hex}"


def generate_transformation_run_id() -> str:
    return f"tf_run_{uuid4().hex}"


def generate_dbt_artifact_id() -> str:
    return f"dbt_art_{uuid4().hex}"


def generate_data_flow_node_id() -> str:
    return f"flow_node_{uuid4().hex}"


def generate_data_flow_edge_id() -> str:
    return f"flow_edge_{uuid4().hex}"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_dataset_id,
    )
    demo_session_id: Mapped[str] = mapped_column(
        ForeignKey("demo_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    raw_table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    files: Mapped[list[DatasetFile]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    column_profiles: Mapped[list[ColumnProfile]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="ColumnProfile.column_index",
    )
    semantic_columns: Mapped[list[SemanticColumn]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="SemanticColumn.raw_column_name",
    )
    question_suggestions: Mapped[list[DatasetQuestionSuggestion]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetQuestionSuggestion.sort_order",
    )
    provider_runs: Mapped[list[AiProviderRun]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="AiProviderRun.created_at",
    )
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="AnalysisRun.created_at",
    )
    transformation_runs: Mapped[list[DatasetTransformationRun]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetTransformationRun.created_at",
    )
    dbt_artifacts: Mapped[list[DbtArtifact]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DbtArtifact.created_at",
    )
    data_flow_nodes: Mapped[list[DataFlowNode]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DataFlowNode.created_at",
    )
    data_flow_edges: Mapped[list[DataFlowEdge]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DataFlowEdge.created_at",
    )


class DatasetFile(Base):
    __tablename__ = "dataset_files"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_dataset_file_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="files")
    column_profiles: Mapped[list[ColumnProfile]] = relationship(
        back_populates="dataset_file",
        cascade="all, delete-orphan",
    )


class ColumnProfile(Base):
    __tablename__ = "column_profiles"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_column_profile_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    column_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    snowflake_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_type: Mapped[str] = mapped_column(String(32), nullable=False)
    null_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    null_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_values_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parse_stats_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="column_profiles")
    dataset_file: Mapped[DatasetFile | None] = relationship(back_populates="column_profiles")
    semantic_columns: Mapped[list[SemanticColumn]] = relationship(
        back_populates="column_profile",
        cascade="all, delete-orphan",
    )


class SemanticColumn(Base):
    __tablename__ = "semantic_columns"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_semantic_column_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_profile_id: Mapped[str] = mapped_column(
        ForeignKey("column_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    suggested_name: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_role: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    approved_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    include_in_model: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    user_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="semantic_columns")
    column_profile: Mapped[ColumnProfile] = relationship(back_populates="semantic_columns")


class DatasetQuestionSuggestion(Base):
    __tablename__ = "dataset_question_suggestions"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_question_suggestion_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="question_suggestions")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_analysis_run_id,
    )
    demo_session_id: Mapped[str] = mapped_column(
        ForeignKey("demo_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_question: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metrics_json: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    dimensions_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    filters_json: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_schema_json: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    preview_rows_json: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failed_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider_chain_json: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="analysis_runs")
    provider_runs: Mapped[list[AiProviderRun]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        order_by="AiProviderRun.created_at",
    )
    charts: Mapped[list[AnalysisRunChart]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        order_by="AnalysisRunChart.sort_order",
    )


class AnalysisRunChart(Base):
    __tablename__ = "analysis_run_charts"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_analysis_run_chart_id,
    )
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chart_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chart_spec_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    data_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    source_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metric_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dimension_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="charts")


class AiProviderRun(Base):
    __tablename__ = "ai_provider_runs"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_provider_run_id,
    )
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    analysis_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    fallback_from_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    dataset: Mapped[Dataset | None] = relationship(back_populates="provider_runs")
    analysis_run: Mapped[AnalysisRun | None] = relationship(back_populates="provider_runs")


class DatasetTransformationRun(Base):
    __tablename__ = "dataset_transformation_runs"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_transformation_run_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dbt_project_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dbt_target_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dbt_run_summary_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="transformation_runs")
    artifacts: Mapped[list[DbtArtifact]] = relationship(
        back_populates="transformation_run",
        cascade="all, delete-orphan",
    )


class DbtArtifact(Base):
    __tablename__ = "dbt_artifacts"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_dbt_artifact_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transformation_run_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_transformation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    layer: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="dbt_artifacts")
    transformation_run: Mapped[DatasetTransformationRun] = relationship(
        back_populates="artifacts",
    )


class DataFlowNode(Base):
    __tablename__ = "data_flow_nodes"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_data_flow_node_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="data_flow_nodes")
    outgoing_edges: Mapped[list[DataFlowEdge]] = relationship(
        back_populates="from_node",
        cascade="all, delete-orphan",
        foreign_keys="DataFlowEdge.from_node_id",
    )
    incoming_edges: Mapped[list[DataFlowEdge]] = relationship(
        back_populates="to_node",
        cascade="all, delete-orphan",
        foreign_keys="DataFlowEdge.to_node_id",
    )


class DataFlowEdge(Base):
    __tablename__ = "data_flow_edges"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_data_flow_edge_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_node_id: Mapped[str] = mapped_column(
        ForeignKey("data_flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_node_id: Mapped[str] = mapped_column(
        ForeignKey("data_flow_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="data_flow_edges")
    from_node: Mapped[DataFlowNode] = relationship(
        back_populates="outgoing_edges",
        foreign_keys=[from_node_id],
    )
    to_node: Mapped[DataFlowNode] = relationship(
        back_populates="incoming_edges",
        foreign_keys=[to_node_id],
    )
