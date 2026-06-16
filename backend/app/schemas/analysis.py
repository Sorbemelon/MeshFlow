from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.dataset import ProviderRunSummary


AnalysisRunStatus = Literal[
    "planning",
    "validating",
    "running",
    "completed",
    "failed",
    "reused",
]
AnalysisDecisionType = Literal[
    "create_new",
    "reuse_existing",
    "needs_user_confirmation",
]
ChartType = Literal["kpi", "line", "bar", "horizontal_bar", "table"]
ChartGenerationStatus = Literal["not_started", "completed", "failed"]


class AnalysisRunCreateRequest(BaseModel):
    attached_dataset_id: str | None = None
    question: str = Field(min_length=1, max_length=500)
    force_new: bool = False


class AnalysisMetricSummary(BaseModel):
    name: str
    aggregation: str


class AnalysisRunSummary(BaseModel):
    id: str
    demo_session_id: str
    dataset_id: str
    question: str
    normalized_question: str
    status: AnalysisRunStatus
    decision_type: AnalysisDecisionType
    intent: str | None = None
    source_model: str | None = None
    grain: str | None = None
    metrics: list[dict[str, Any]]
    dimensions: list[str]
    filters: list[dict[str, Any]]
    row_count: int | None = None
    error_code: str | None = None
    failed_step: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class AnalysisRunDetail(AnalysisRunSummary):
    generated_sql: str | None = None
    output_schema: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    provider_chain: list[dict[str, Any]]
    provider_runs: list[ProviderRunSummary]


class AnalysisRunChartSummary(BaseModel):
    id: str
    analysis_run_id: str
    dataset_id: str
    chart_type: ChartType
    title: str
    description: str | None = None
    chart_spec: dict[str, Any]
    data: list[dict[str, Any]]
    source_model: str | None = None
    metric_summary: str | None = None
    dimension_summary: str | None = None
    sort_order: int
    created_at: str


class AnalysisRunResponse(BaseModel):
    analysis_run: AnalysisRunDetail
    charts: list[AnalysisRunChartSummary] = Field(default_factory=list)
    chart_generation_status: ChartGenerationStatus = "not_started"
    chart_generation_message: str | None = None
    reused: bool = False


class AnalysisRunListResponse(BaseModel):
    analysis_runs: list[AnalysisRunSummary]
