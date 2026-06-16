from __future__ import annotations

import csv
import io
import re
from pathlib import PurePath

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.demo_session import DemoSession
from app.schemas.upload_preflight import (
    ReadinessCheck,
    UploadFileValidation,
    UploadPreflightResponse,
    UploadQuotaSummary,
    UploadReadinessSummary,
)
from app.services import readiness_service
from app.services.demo_session_service import (
    configured_limits,
    get_required_session,
    usage_from_session,
)


PREVIEW_ROW_LIMIT = 25
BYTES_PER_MB = 1024 * 1024


def _empty_file_result(file_name: str = "") -> UploadFileValidation:
    extension = PurePath(file_name).suffix.lower() if file_name else ""
    return UploadFileValidation(
        file_name=file_name,
        size_bytes=0,
        size_mb=0.0,
        extension=extension,
        detected_format="csv" if extension == ".csv" else None,
        valid=False,
        row_count_previewed=0,
        column_count=0,
        headers=[],
        warnings=[],
        errors=[],
    )


def _not_checked(message: str) -> ReadinessCheck:
    return ReadinessCheck(
        status="not_checked",
        message=message,
        next_action="Resolve validation and quota checks before upload readiness is evaluated.",
    )


def _size_mb(size_bytes: int) -> float:
    return round(size_bytes / BYTES_PER_MB, 4)


def _normalize_column_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_").upper()
    if normalized and normalized[0].isdigit():
        normalized = f"COL_{normalized}"
    return normalized


def _file_too_large_result(file_name: str, content: bytes, limit_mb: int) -> UploadFileValidation:
    result = _empty_file_result(file_name)
    result.size_bytes = len(content)
    result.size_mb = _size_mb(len(content))
    result.errors.append("FILE_TOO_LARGE")
    result.warnings.append(f"File must be {limit_mb} MB or smaller.")
    return result


def _validate_csv_content(file_name: str, content: bytes, limit_mb: int) -> UploadFileValidation:
    result = _empty_file_result(file_name)
    result.size_bytes = len(content)
    result.size_mb = _size_mb(len(content))

    if not file_name:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("A CSV file is required.")
        return result

    if result.extension != ".csv":
        result.errors.append("INVALID_FILE_TYPE")
        result.warnings.append("Only .csv files are supported in the MVP.")
        return result

    if not content:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The selected CSV is empty.")
        return result

    if len(content) > limit_mb * BYTES_PER_MB:
        return _file_too_large_result(file_name, content, limit_mb)

    if b"\x00" in content:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The selected file appears to contain unsupported binary content.")
        return result

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The CSV must be encoded as UTF-8.")
        return result

    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The CSV parser could not read the selected file.")
        return result

    if not rows:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The CSV must include a header row.")
        return result

    headers = rows[0]
    result.headers = headers
    result.column_count = len(headers)
    if not headers:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The CSV must include a header row.")
        return result

    if len(headers) < 2:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The CSV must include at least two columns.")

    stripped_headers = [header.strip() for header in headers]
    if any(not header for header in stripped_headers):
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("Headers must not be empty.")

    normalized_headers = [_normalize_column_name(header) for header in headers]
    if any(not header for header in normalized_headers):
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("Headers must produce Snowflake-safe column names.")

    if len(set(normalized_headers)) != len(normalized_headers):
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("Headers must be unique after normalization.")

    data_rows = [row for row in rows[1:] if any(cell.strip() for cell in row)]
    result.row_count_previewed = min(len(data_rows), PREVIEW_ROW_LIMIT)
    if not data_rows:
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("The CSV must include at least one data row.")
    elif any(len(row) != len(headers) for row in data_rows[:PREVIEW_ROW_LIMIT]):
        result.errors.append("INVALID_CSV_FORMAT")
        result.warnings.append("Previewed rows must have the same width as the header row.")

    result.valid = not result.errors
    return result


def _quota_summary(session: DemoSession, file_size_mb: float, config: Settings) -> UploadQuotaSummary:
    limits = configured_limits(config)
    usage = usage_from_session(session)
    quota = UploadQuotaSummary(
        uploaded_datasets_used=usage.uploaded_datasets_used,
        uploaded_datasets_limit=limits.max_uploaded_datasets_per_session,
        total_upload_mb_used=usage.total_upload_mb_used,
        total_upload_mb_limit=limits.max_total_upload_size_mb,
        file_size_mb_limit=limits.max_upload_file_size_mb,
    )

    if usage.uploaded_datasets_used >= limits.max_uploaded_datasets_per_session:
        quota.errors.append("UPLOAD_LIMIT_REACHED")

    if usage.total_upload_mb_used + file_size_mb > limits.max_total_upload_size_mb:
        quota.errors.append("TOTAL_UPLOAD_LIMIT_REACHED")

    return quota


async def run_upload_preflight(
    db: Session,
    session_id: str | None,
    file: UploadFile | None,
    config: Settings = settings,
) -> UploadPreflightResponse:
    session = get_required_session(db, session_id)
    limits = configured_limits(config)
    read_limit = limits.max_upload_file_size_mb * BYTES_PER_MB + 1

    if file is None:
        file_result = _empty_file_result()
        file_result.errors.append("INVALID_CSV_FORMAT")
        file_result.warnings.append("A CSV file is required.")
    else:
        content = await file.read(read_limit)
        file_result = _validate_csv_content(
            file.filename or "",
            content,
            limits.max_upload_file_size_mb,
        )

    quota = _quota_summary(session, file_result.size_mb, config)

    if file_result.valid and not quota.errors:
        s3_readiness = readiness_service.check_s3_readiness(config)
        snowflake_readiness = readiness_service.check_snowflake_readiness(config)
    else:
        s3_readiness = _not_checked("S3 readiness was not checked because preflight is blocked.")
        snowflake_readiness = _not_checked(
            "Snowflake readiness was not checked because preflight is blocked."
        )

    can_upload = (
        file_result.valid
        and not quota.errors
        and s3_readiness.status == "ready"
        and snowflake_readiness.status == "ready"
    )
    status = "ready" if can_upload else "blocked"

    if file_result.errors:
        message = "Upload preflight is blocked by CSV validation."
    elif quota.errors:
        message = "Upload preflight is blocked by public demo limits."
    elif not can_upload:
        message = "Upload preflight is blocked by readiness checks."
    else:
        message = "Upload preflight passed. Upload execution is not performed in this phase."

    return UploadPreflightResponse(
        status=status,
        can_upload=can_upload,
        file=file_result,
        quota=quota,
        readiness=UploadReadinessSummary(
            s3=s3_readiness,
            snowflake=snowflake_readiness,
        ),
        message=message,
    )
