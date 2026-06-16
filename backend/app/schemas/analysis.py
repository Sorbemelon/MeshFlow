from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.dashboard import DashboardCardSummary
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
InsightGenerationStatus = Literal["not_started", "completed", "failed"]
InsightLevel = Literal["question", "chart"]
InsightStatus = Literal["completed", "failed"]


class AnalysisRunCreateRequest(BaseModel):
    attached_dataset_id: str | None = None
    question: str = Field(min_length=1, max_length=500)
    force_new: bool = False
    save_to_dashboard: bool = False


class AnalysisMetricSummary(BaseModel):
    name: str
    aggregation: str


class AnalysisRunSummary(BaseModel):
    id: str
    demo_session_id: str
    dataset_id: str
    dataset_name: str | None = None
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
    chart_count: int = 0
    insight_status: InsightGenerationStatus = "not_started"
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


class AnalysisInsightSummary(BaseModel):
    id: str
    analysis_run_id: str
    analysis_run_chart_id: str | None = None
    insight_level: InsightLevel
    status: InsightStatus
    summary: str | None = None
    key_findings: list[str]
    tags: list[str]
    confidence: str | None = None
    provider_name: str | None = None
    provider_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class AnalysisRunResponse(BaseModel):
    analysis_run: AnalysisRunDetail
    charts: list[AnalysisRunChartSummary] = Field(default_factory=list)
    insights: list[AnalysisInsightSummary] = Field(default_factory=list)
    chart_generation_status: ChartGenerationStatus = "not_started"
    chart_generation_message: str | None = None
    insight_generation_status: InsightGenerationStatus = "not_started"
    insight_generation_message: str | None = None
    saved_dashboard_card: DashboardCardSummary | None = None
    dashboard_card_created: bool = False
    dashboard_card_message: str | None = None
    reused: bool = False


class AnalysisRunListResponse(BaseModel):
    analysis_runs: list[AnalysisRunSummary]
