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


def _safe_file_name(file_name: str) -> str:
    name = PurePath(file_name).name.strip() or "upload.csv"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return safe.strip("._") or "upload.csv"


def build_storage_key(
    session_id: str,
    dataset_id: str,
    file_name: str,
    config: Settings = settings,
) -> str:
    prefix = config.s3_upload_prefix.strip().strip("/")
    parts = [part for part in [prefix, "sessions", session_id, "raw", dataset_id, _safe_file_name(file_name)] if part]
    return "/".join(parts)


def upload_csv_to_s3(
    *,
    session_id: str,
    dataset_id: str,
    file_name: str,
    content: bytes,
    content_type: str | None,
    config: Settings = settings,
) -> StorageUploadResult:
    bucket = config.configured_s3_bucket
    if not bucket:
        raise StorageServiceError("S3 bucket is not configured.")

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise StorageServiceError(
            "boto3 is not installed. Install backend requirements before uploading to S3."
        ) from exc

    key = build_storage_key(session_id, dataset_id, file_name, config)

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
    bucket = config.configured_s3_bucket
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
