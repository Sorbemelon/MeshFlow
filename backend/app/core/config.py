from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Phase 1 intentionally configures only the backend foundation.
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
    debug: bool = Field(default=True, alias="DEBUG")

    # Metadata database only. This must not be used as an analytical engine.
    database_url: str = Field(
        default="sqlite:///./.local/meshflow_metadata.db", alias="DATABASE_URL"
    )

    allow_demo_reset_usage: bool = Field(default=True, alias="ALLOW_DEMO_RESET_USAGE")

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
