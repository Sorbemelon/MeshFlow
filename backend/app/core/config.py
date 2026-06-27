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

    # Future phases only.
    aws_region: str | None = Field(default=None, alias="AWS_REGION")
    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    s3_upload_prefix: str = Field(default="meshflow-demo", alias="S3_UPLOAD_PREFIX")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")

    snowflake_account: str | None = Field(default=None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str | None = Field(default=None, alias="SNOWFLAKE_USER")
    snowflake_password: str | None = Field(default=None, alias="SNOWFLAKE_PASSWORD")
    snowflake_role: str | None = Field(default=None, alias="SNOWFLAKE_ROLE")
    snowflake_warehouse: str | None = Field(default=None, alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str | None = Field(default=None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str | None = Field(default=None, alias="SNOWFLAKE_SCHEMA")
    snowflake_stage_name: str | None = Field(default=None, alias="SNOWFLAKE_STAGE_NAME")

    dbt_runtime_dir: str = Field(default="./.local/dbt", alias="DBT_RUNTIME_DIR")
    dbt_projects_dir: str = Field(default="./.local/dbt_projects", alias="DBT_PROJECTS_DIR")
    dbt_profiles_dir: str | None = Field(default=None, alias="DBT_PROFILES_DIR")
    dbt_target_name: str = Field(default="dev", alias="DBT_TARGET_NAME")
    dbt_threads: int = Field(default=1, alias="DBT_THREADS")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str | None = Field(default=None, alias="OPENAI_MODEL")
    gemini_api_key_1: str | None = Field(default=None, alias="GEMINI_API_KEY_1")
    gemini_api_key_2: str | None = Field(default=None, alias="GEMINI_API_KEY_2")
    gemini_model_1: str | None = Field(default=None, alias="GEMINI_MODEL_1")
    gemini_model_2: str | None = Field(default=None, alias="GEMINI_MODEL_2")

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
