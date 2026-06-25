from app.core.config import Settings, settings
from app.schemas.upload_preflight import ReadinessCheck
from app.services import snowflake_service


def _missing(names: dict[str, str | None]) -> list[str]:
    return [name for name, value in names.items() if not value]


def check_s3_readiness(config: Settings = settings) -> ReadinessCheck:
    missing = _missing(
        {
            "AWS_REGION": config.aws_region,
            "AWS_ACCESS_KEY_ID": config.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": config.aws_secret_access_key,
            "S3_BUCKET_NAME": config.s3_bucket_name,
        }
    )
    if missing:
        return ReadinessCheck(
            status="not_configured",
            message="S3 is not configured for uploads.",
            next_action=f"Set {', '.join(missing)} before enabling uploads.",
        )

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return ReadinessCheck(
            status="failed",
            message="S3 configuration is present, but boto3 is not installed.",
            next_action="Install backend requirements before enabling uploads.",
        )

    try:
        client = boto3.client(
            "s3",
            region_name=config.aws_region,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        client.head_bucket(Bucket=config.s3_bucket_name)
    except (BotoCoreError, ClientError):
        return ReadinessCheck(
            status="failed",
            message="S3 readiness check failed for the configured bucket.",
            next_action="Verify AWS credentials, region, bucket name, and bucket permissions.",
        )

    return ReadinessCheck(
        status="ready",
        message="S3 bucket readiness check passed.",
        next_action=None,
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
            "SNOWFLAKE_STAGE_NAME": config.snowflake_stage_name,
        }
    )
    if missing:
        return ReadinessCheck(
            status="not_configured",
            message="Snowflake is not configured for Warehouse Raw loading.",
            next_action=f"Set {', '.join(missing)} before enabling uploads.",
        )

    try:
        snowflake_service.check_connection_and_stage(config)
    except snowflake_service.SnowflakeServiceError as exc:
        message = str(exc) or "Snowflake readiness check failed."
        return ReadinessCheck(
            status="failed",
            message=message,
            next_action=(
                "Verify Snowflake credentials, database, schema, warehouse, role, "
                "external stage access, and SNOWFLAKE_STAGE_NAME qualification."
            ),
        )

    return ReadinessCheck(
        status="ready",
        message="Snowflake warehouse and stage readiness check passed.",
        next_action=None,
    )
