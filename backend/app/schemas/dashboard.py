from typing import Any, Literal

from pydantic import BaseModel, Field


DashboardCardType = Literal["result_group", "chart"]
DashboardCardStatus = Literal["active", "archived"]


class DashboardCardSummary(BaseModel):
    id: str
    demo_session_id: str
    dataset_id: str | None = None
    analysis_run_id: str | None = None
    analysis_run_chart_id: str | None = None
    card_type: DashboardCardType
    title: str
    subtitle: str | None = None
    dataset_name_snapshot: str | None = None
    source_model_snapshot: str | None = None
    card_snapshot: dict[str, Any]
    sort_order: int
    status: DashboardCardStatus
    archived_at: str | None = None
    created_at: str
    updated_at: str


class DashboardCardCreateRequest(BaseModel):
    analysis_run_id: str = Field(min_length=1)


class DashboardResponse(BaseModel):
    dashboard_count: int
    cards: list[DashboardCardSummary]
    cards_used: int
    cards_limit: int
    visible_card_count: int


class DashboardCardMutationResponse(BaseModel):
    card: DashboardCardSummary
    cards_used: int
    cards_limit: int
    created: bool = False
    message: str | None = None
