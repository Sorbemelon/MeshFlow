from app.core.config import Settings, settings
from app.schemas.upload_preflight import ReadinessCheck


def _missing(names: dict[str, str | None]) -> list[str]:
    return [name for name, value in names.items() if not value]


def check_s3_readiness(config: Settings = settings) -> ReadinessCheck:
    missing = _missing(
        {
            "AWS_REGION": config.aws_region,
            "AWS_ACCESS_KEY_ID": config.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": config.aws_secret_access_key,
            "S3_BUCKET_NAME": config.configured_s3_bucket,
        }
    )
    if missing:
        return ReadinessCheck(
            status="not_configured",
            message="S3 is not configured for upload preflight.",
            next_action=f"Set {', '.join(missing)} before enabling uploads.",
        )

    return ReadinessCheck(
        status="not_checked",
        message="S3 configuration is present, but live S3 readiness is not checked yet.",
        next_action="Add a lightweight S3 readiness check before enabling upload execution.",
    )


def check_snowflake_readiness(config: Settings = settings) -> ReadinessCheck:
    missing = _missing(
        {
            "SNOWFLAKE_ACCOUNT": config.snowflake_account,
            "SNOWFLAKE_USER": config.snowflake_user,
            "SNOWFLAKE_PASSWORD": config.snowflake_password,
            "SNOWFLAKE_ROLE": config.snowflake_role,
            "SNOWFLAKE_WAREHOUSE": config.snowflake_warehouse,
            "SNOWFLAKE_DATABASE": config.snowflake_database,
            "SNOWFLAKE_SCHEMA": config.snowflake_schema,
        }
    )
    if missing:
        return ReadinessCheck(
            status="not_configured",
            message="Snowflake is not configured for upload preflight.",
            next_action=f"Set {', '.join(missing)} before enabling uploads.",
        )

    return ReadinessCheck(
        status="not_checked",
        message="Snowflake configuration is present, but live Snowflake readiness is not checked yet.",
        next_action="Add a lightweight Snowflake readiness check before enabling upload execution.",
    )
