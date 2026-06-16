from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.demo_session import DemoSessionSummary
from app.schemas.limits import DemoLimits


class DashboardSummary(BaseModel):
    dashboard_count: int
    cards: list[dict[str, Any]]
    cards_used: int
    cards_limit: int


class HistorySummary(BaseModel):
    analysis_runs: list[dict[str, Any]]
    successful_analysis_runs_used: int
    successful_analysis_runs_limit: int


class WorkspaceSetupStatus(BaseModel):
    backend: Literal["available"]
    storage: Literal["not_checked"]
    warehouse: Literal["not_checked"]
    dbt: Literal["not_checked"]
    ai: Literal["not_checked"]


class WorkspaceResponse(BaseModel):
    session: DemoSessionSummary
    datasets: list[dict[str, Any]]
    ready_datasets: list[dict[str, Any]]
    active_dataset: dict[str, Any] | None
    dashboard: DashboardSummary
    history: HistorySummary
    limits: DemoLimits
    setup_status: WorkspaceSetupStatus
