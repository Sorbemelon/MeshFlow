from typing import Literal

from pydantic import BaseModel, Field


DatasetSourceType = Literal["uploaded_csv", "demo_raw_retail"]
DatasetStatus = Literal[
    "schema_review",
    "warehouse_loaded",
    "transforming",
    "ready_for_analysis",
    "transform_failed",
    "failed",
    "deleted",
]
DetectedColumnType = Literal[
    "date",
    "integer",
    "decimal",
    "boolean",
    "string",
    "identifier",
    "unknown",
]
SemanticRole = Literal[
    "identifier",
    "date_time",
    "measure_column",
    "metric_candidate",
    "dimension",
    "unknown",
]
SemanticPreparationStatus = Literal["not_started", "running", "completed", "failed"]
QuestionSuggestionStatus = Literal["not_started", "completed", "failed"]
TransformationStatus = Literal["not_started", "pending", "running", "completed", "failed"]
DataFlowNodeStatus = Literal["not_started", "waiting", "running", "completed", "failed"]
CleanupStatus = Literal["completed", "skipped", "failed", "not_configured"]


class CleanupSummary(BaseModel):
    s3: CleanupStatus = "skipped"
    snowflake: CleanupStatus = "skipped"
    dbt_runtime: CleanupStatus = "skipped"
    warnings: list[str] = Field(default_factory=list)


class ColumnProfileSummary(BaseModel):
    id: str
    column_index: int
    raw_column_name: str
    normalized_column_name: str
    snowflake_column_name: str
    detected_type: DetectedColumnType
    null_count: int
    null_rate: float
    unique_count: int | None = None
    sample_values: list[str]


class SchemaPreview(BaseModel):
    columns: list[ColumnProfileSummary]


class SemanticColumnSummary(BaseModel):
    id: str
    column_profile_id: str
    raw_column_name: str
    suggested_name: str
    semantic_role: SemanticRole
    confidence: float
    needs_review: bool
    reason: str
    approved_name: str | None = None
    approved_role: SemanticRole | None = None
    include_in_model: bool
    user_edited: bool
    provider_name: str | None = None
    provider_model: str | None = None


class DatasetQuestionSuggestionSummary(BaseModel):
    id: str
    question: str
    intent: str | None = None
    sort_order: int
    provider_name: str | None = None
    provider_model: str | None = None


class ProviderRunSummary(BaseModel):
    id: str
    task_type: str
    provider_name: str
    provider_model: str | None = None
    status: str
    error_code: str | None = None
    error_message: str | None = None
    fallback_from_provider: str | None = None
    latency_ms: int | None = None
    created_at: str


class SemanticPreparationResponse(BaseModel):
    status: SemanticPreparationStatus
    message: str
    semantic_columns: list[SemanticColumnSummary]
    provider_runs: list[ProviderRunSummary]
    next_action: str | None = None


class QuestionSuggestionsResponse(BaseModel):
    status: QuestionSuggestionStatus
    message: str
    suggestions: list[DatasetQuestionSuggestionSummary]
    generated_from: Literal["data_marts"] = "data_marts"
    provider_runs: list[ProviderRunSummary]
    next_action: str | None = None


class DatasetSummary(BaseModel):
    id: str
    name: str
    source_type: DatasetSourceType
    status: DatasetStatus
    row_count: int
    column_count: int
    raw_table_name: str
    created_at: str
    deleted_at: str | None = None


class DatasetFileSummary(BaseModel):
    file_name: str
    size_bytes: int
    storage_key: str
    checksum_sha256: str | None = None


class DatasetDetailResponse(BaseModel):
    dataset: DatasetSummary
    file: DatasetFileSummary | None = None
    schema_preview: SchemaPreview
    semantic_preparation: SemanticPreparationResponse
    question_suggestions: QuestionSuggestionsResponse


class DbtArtifactSummary(BaseModel):
    id: str
    artifact_type: str
    layer: str
    name: str
    content_redacted: str
    file_path: str | None = None
    created_at: str


class DatasetTransformationRunSummary(BaseModel):
    id: str
    status: TransformationStatus
    started_at: str
    completed_at: str | None = None
    failed_step: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    dbt_project_path: str | None = None
    dbt_target_name: str | None = None
    dbt_run_summary: dict[str, object] | None = None


class DataFlowNodeSummary(BaseModel):
    id: str
    node_type: str
    name: str
    label: str
    status: DataFlowNodeStatus
    metadata: dict[str, object] | None = None


class DataFlowEdgeSummary(BaseModel):
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    metadata: dict[str, object] | None = None


class DatasetDataFlowResponse(BaseModel):
    dataset: DatasetSummary
    transformation: DatasetTransformationRunSummary | None = None
    nodes: list[DataFlowNodeSummary]
    edges: list[DataFlowEdgeSummary]
    artifacts: list[DbtArtifactSummary]
    models: dict[str, list[str]]
    question_suggestions: QuestionSuggestionsResponse


class DatasetTransformRequest(BaseModel):
    force: bool = False


class DatasetTransformResponse(BaseModel):
    status: Literal["completed"]
    dataset: DatasetSummary
    transformation_run: DatasetTransformationRunSummary
    layers_completed: list[str]
    models: dict[str, list[str]]
    next_route: str


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class DatasetDeleteResponse(BaseModel):
    status: Literal["deleted", "already_deleted"]
    dataset_id: str
    message: str
    quota_restored: bool = False
    cleanup: CleanupSummary


class DatasetUploadResponse(BaseModel):
    status: Literal["uploaded", "already_exists"]
    message: str | None = None
    dataset: DatasetSummary
    file: DatasetFileSummary
    schema_preview: SchemaPreview
    next_route: str


class SemanticPreparationRunRequest(BaseModel):
    force: bool = False


class SemanticColumnMappingUpdate(BaseModel):
    column_profile_id: str
    approved_name: str
    approved_role: str
    include_in_model: bool = True


class SemanticColumnMappingPatchRequest(BaseModel):
    columns: list[SemanticColumnMappingUpdate]
