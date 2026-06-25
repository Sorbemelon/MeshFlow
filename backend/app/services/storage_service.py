from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePath

from app.core.config import Settings, settings


class StorageServiceError(Exception):
    pass


@dataclass
class StorageUploadResult:
    storage_key: str
    storage_uri: str


@dataclass(frozen=True)
class CleanupOperationResult:
    status: str
    warning: str | None = None


def _safe_file_name(file_name: str) -> str:
    name = PurePath(file_name).name.strip() or "upload.csv"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return safe.strip("._") or "upload.csv"


def build_storage_key(
    session_id: str,
    dataset_id: str,
    file_name: str,
    storage_group: str = "raw",
    config: Settings = settings,
) -> str:
    prefix = config.s3_upload_prefix.strip().strip("/")
    safe_group = re.sub(r"[^A-Za-z0-9._-]+", "_", storage_group.strip()) or "raw"
    parts = [
        part
        for part in [
            prefix,
            "sessions",
            session_id,
            safe_group,
            dataset_id,
            _safe_file_name(file_name),
        ]
        if part
    ]
    return "/".join(parts)


def upload_csv_to_s3(
    *,
    session_id: str,
    dataset_id: str,
    file_name: str,
    content: bytes,
    content_type: str | None,
    storage_group: str = "raw",
    config: Settings = settings,
) -> StorageUploadResult:
    bucket = config.s3_bucket_name
    if not bucket:
        raise StorageServiceError("S3 bucket is not configured.")

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise StorageServiceError(
            "boto3 is not installed. Install backend requirements before uploading to S3."
        ) from exc

    key = build_storage_key(session_id, dataset_id, file_name, storage_group, config)

    try:
        client = boto3.client(
            "s3",
            region_name=config.aws_region,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type or "text/csv",
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageServiceError("S3 upload failed.") from exc

    return StorageUploadResult(storage_key=key, storage_uri=f"s3://{bucket}/{key}")


def delete_s3_object(
    *,
    storage_key: str,
    config: Settings = settings,
) -> None:
    bucket = config.s3_bucket_name
    if not bucket:
        return

    try:
        import boto3
    except ImportError:
        return

    try:
        client = boto3.client(
            "s3",
            region_name=config.aws_region,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        client.delete_object(Bucket=bucket, Key=storage_key)
    except Exception:
        # Rollback cleanup is best-effort only. Upload service still reports the
        # real Snowflake failure that caused rollback.
        return


def delete_s3_object_for_cleanup(
    *,
    storage_key: str | None,
    config: Settings = settings,
) -> CleanupOperationResult:
    if not storage_key:
        return CleanupOperationResult(status="skipped")

    bucket = config.s3_bucket_name
    if not bucket:
        return CleanupOperationResult(
            status="not_configured",
            warning="S3 cleanup skipped because no S3 bucket is configured.",
        )

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return CleanupOperationResult(
            status="failed",
            warning="S3 cleanup could not run because boto3 is not installed.",
        )

    try:
        client = boto3.client(
            "s3",
            region_name=config.aws_region,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        client.delete_object(Bucket=bucket, Key=storage_key)
    except (BotoCoreError, ClientError) as exc:
        return CleanupOperationResult(
            status="failed",
            warning=f"S3 cleanup failed for object key {storage_key}: {exc.__class__.__name__}.",
        )

    return CleanupOperationResult(status="completed")
