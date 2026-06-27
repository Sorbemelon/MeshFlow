from pydantic import BaseModel


class DemoLimits(BaseModel):
    retention_days: int
    max_upload_file_size_mb: int
    max_total_upload_size_mb: int
    max_successful_analysis_runs_per_session: int
    max_dashboard_cards_per_session: int
    preferred_charts_per_analysis: int = 1
    max_charts_per_analysis: int
    dashboards_per_session: int


class DemoUsage(BaseModel):
    successful_uploads_used: int
    uploaded_datasets_used: int
    successful_analysis_runs_used: int
    dashboard_cards_used: int
    total_upload_mb_used: float


class LimitsResponse(BaseModel):
    limits: DemoLimits
    usage: DemoUsage | None = None
