from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for metadata-backed backend phases.

    Warehouse/S3/dbt/AI settings are declared for future phases but are not used yet.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="MeshFlow API", alias="APP_NAME")
    app_env: Literal["development", "test", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=True, alias="APP_DEBUG")
    backend_cors_origins: str = Field(
        default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS"
    )

    # Metadata database only. This must not be used as an analytical engine.
    database_url: str = Field(
        default="sqlite:///./.local/meshflow_metadata.db", alias="DATABASE_URL"
    )

    demo_session_retention_days: int = Field(
        default=3, alias="DEMO_SESSION_RETENTION_DAYS"
    )
    max_demo_datasets_per_session: int = Field(
        default=1, alias="MAX_DEMO_DATASETS_PER_SESSION"
    )
    max_uploaded_datasets_per_session: int = Field(
        default=1, alias="MAX_UPLOADED_DATASETS_PER_SESSION"
    )
    max_upload_file_size_mb: int = Field(default=5, alias="MAX_UPLOAD_FILE_SIZE_MB")
    max_total_upload_size_mb: int = Field(default=10, alias="MAX_TOTAL_UPLOAD_SIZE_MB")
    max_successful_analysis_runs_per_session: int = Field(
        default=8, alias="MAX_SUCCESSFUL_ANALYSIS_RUNS_PER_SESSION"
    )
    max_dashboard_cards_per_session: int = Field(
        default=8, alias="MAX_DASHBOARD_CARDS_PER_SESSION"
    )
    max_charts_per_analysis: int = Field(default=3, alias="MAX_CHARTS_PER_ANALYSIS")
    dashboards_per_session: int = Field(default=1, alias="DASHBOARDS_PER_SESSION")
    allow_demo_reset_usage: bool = Field(default=False, alias="ALLOW_DEMO_RESET_USAGE")

    # Future phases only.
    aws_region: str | None = Field(default=None, alias="AWS_REGION")
    aws_s3_bucket: str | None = Field(default=None, alias="AWS_S3_BUCKET")

    snowflake_account: str | None = Field(default=None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str | None = Field(default=None, alias="SNOWFLAKE_USER")
    snowflake_role: str | None = Field(default=None, alias="SNOWFLAKE_ROLE")
    snowflake_warehouse: str | None = Field(default=None, alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str | None = Field(default=None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str | None = Field(default=None, alias="SNOWFLAKE_SCHEMA")

    openai_model: str | None = Field(default=None, alias="OPENAI_MODEL")
    gemini_model_1: str | None = Field(default=None, alias="GEMINI_MODEL_1")
    gemini_model_2: str | None = Field(default=None, alias="GEMINI_MODEL_2")
    gemini_model_3: str | None = Field(default=None, alias="GEMINI_MODEL_3")

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
