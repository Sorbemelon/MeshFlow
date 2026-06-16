from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.core.errors import AppError
from app.models.dataset import (
    ColumnProfile,
    Dataset,
    DatasetFile,
    generate_dataset_id,
)
from app.schemas.dataset import (
    ColumnProfileSummary,
    DatasetDetailResponse,
    DatasetFileSummary,
    DatasetListResponse,
    DatasetSummary,
    DatasetUploadResponse,
    SchemaPreview,
)
from app.schemas.upload_preflight import ReadinessCheck
from app.services import readiness_service, snowflake_service, storage_service
from app.services.demo_session_service import (
    get_required_session,
)
from app.services.upload_preflight_service import (
    CsvUploadValidation,
    validate_upload_preflight,
)


NULL_STRINGS = {"", "NULL", "null"}
BOOLEAN_STRINGS = {"true", "false", "yes", "no", "y", "n", "0", "1"}
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y")


def _profile_summary(profile: ColumnProfile) -> ColumnProfileSummary:
    return ColumnProfileSummary(
        column_index=profile.column_index,
        raw_column_name=profile.raw_column_name,
        normalized_column_name=profile.normalized_column_name,
        snowflake_column_name=profile.snowflake_column_name,
        detected_type=profile.detected_type,
        null_count=profile.null_count,
        null_rate=profile.null_rate,
        unique_count=profile.unique_count,
        sample_values=profile.sample_values_json,
    )


def dataset_summary(dataset: Dataset) -> DatasetSummary:
    return DatasetSummary(
        id=dataset.id,
        name=dataset.name,
        source_type=dataset.source_type,
        status=dataset.status,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        raw_table_name=dataset.raw_table_name,
        created_at=dataset.created_at.isoformat(),
    )


def dataset_file_summary(dataset_file: DatasetFile) -> DatasetFileSummary:
    return DatasetFileSummary(
        file_name=dataset_file.file_name,
        size_bytes=dataset_file.file_size_bytes,
        storage_key=dataset_file.storage_key,
        checksum_sha256=dataset_file.checksum_sha256,
    )


def schema_preview_from_profiles(profiles: Iterable[ColumnProfile]) -> SchemaPreview:
    return SchemaPreview(columns=[_profile_summary(profile) for profile in profiles])


def _is_null(value: str) -> bool:
    return value.strip() in NULL_STRINGS


def _is_date(value: str) -> bool:
    for date_format in DATE_FORMATS:
        try:
            datetime.strptime(value, date_format)
            return True
        except ValueError:
            continue

    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_integer(value: str) -> bool:
    try:
        int(value)
        return "." not in value
    except ValueError:
        return False


def _is_decimal(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except (InvalidOperation, ValueError):
        return False


def _detect_type(raw_column_name: str, values: list[str]) -> str:
    non_null = [value.strip() for value in values if not _is_null(value)]
    if not non_null:
        return "unknown"

    column_name = raw_column_name.strip().lower()
    if column_name == "id" or column_name.endswith("_id") or column_name.endswith(" id"):
        return "identifier"

    lowered = {value.lower() for value in non_null}
    if lowered <= BOOLEAN_STRINGS:
        return "boolean"

    if all(_is_integer(value) for value in non_null):
        return "integer"

    if all(_is_decimal(value) for value in non_null):
        return "decimal"

    if all(_is_date(value) for value in non_null):
        return "date"

    return "string"


def build_column_profiles(csv: CsvUploadValidation, dataset_file: DatasetFile) -> list[ColumnProfile]:
    rows = csv.data_rows
    row_count = len(rows)
    profiles: list[ColumnProfile] = []

    for index, raw_column_name in enumerate(csv.file.headers):
        values = [row[index].strip() for row in rows]
        null_count = sum(1 for value in values if _is_null(value))
        non_null_values = [value for value in values if not _is_null(value)]
        sample_values = list(dict.fromkeys(non_null_values))[:5]
        profiles.append(
            ColumnProfile(
                dataset=dataset_file.dataset,
                dataset_file=dataset_file,
                column_index=index,
                raw_column_name=raw_column_name,
                normalized_column_name=csv.snowflake_column_names[index],
                snowflake_column_name=csv.snowflake_column_names[index],
                detected_type=_detect_type(raw_column_name, values),
                null_count=null_count,
                null_rate=round(null_count / row_count, 4) if row_count else 0.0,
                unique_count=len(set(non_null_values)),
                sample_values_json=sample_values,
                parse_stats_json={
                    "profile_source": "validated_csv",
                    "semantic_suggestions": "deferred",
                },
            )
        )

    return profiles


def _readiness_error(
    *,
    code: str,
    failed_step: str,
    check: ReadinessCheck,
) -> AppError:
    return AppError(
        error_code=code,
        failed_step=failed_step,
        message=check.message,
        next_action=check.next_action,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _validation_error(errors: list[str], failed_step: str) -> AppError:
    code = errors[0] if errors else "DATASET_UPLOAD_FAILED"
    message = (
        "The selected CSV could not be uploaded because validation failed."
        if code in {"INVALID_FILE_TYPE", "INVALID_CSV_FORMAT", "FILE_TOO_LARGE"}
        else "The selected CSV could not be uploaded because the public demo limit was reached."
    )
    return AppError(
        error_code=code,
        failed_step=failed_step,
        message=message,
        next_action="Resolve the listed upload issue, then retry.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


async def upload_dataset(
    db: Session,
    session_id: str | None,
    file: UploadFile | None,
    config: Settings = settings,
) -> DatasetUploadResponse:
    check = await validate_upload_preflight(db, session_id, file, config)
    if not check.csv.file.valid:
        raise _validation_error(check.csv.file.errors, "upload_validation")
    if check.quota.errors:
        raise _validation_error(check.quota.errors, "upload_quota")

    s3_readiness = readiness_service.check_s3_readiness(config)
    if s3_readiness.status != "ready":
        raise _readiness_error(
            code="S3_NOT_READY",
            failed_step="s3_readiness",
            check=s3_readiness,
        )

    snowflake_readiness = readiness_service.check_snowflake_readiness(config)
    if snowflake_readiness.status != "ready":
        raise _readiness_error(
            code="SNOWFLAKE_NOT_READY",
            failed_step="warehouse_readiness",
            check=snowflake_readiness,
        )

    dataset_id = generate_dataset_id()
    content_type = file.content_type if file else "text/csv"
    try:
        storage_result = storage_service.upload_csv_to_s3(
            session_id=check.session.id,
            dataset_id=dataset_id,
            file_name=check.csv.file.file_name,
            content=check.csv.content,
            content_type=content_type,
            config=config,
        )
    except storage_service.StorageServiceError as exc:
        raise AppError(
            error_code="S3_UPLOAD_FAILED",
            failed_step="s3_upload",
            message="MeshFlow could not upload the CSV to S3.",
            next_action="Check S3 configuration and permissions, then retry.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    try:
        load_result = snowflake_service.create_and_load_raw_table(
            dataset_id=dataset_id,
            snowflake_columns=check.csv.snowflake_column_names,
            storage_key=storage_result.storage_key,
            config=config,
        )
    except snowflake_service.SnowflakeServiceError as exc:
        storage_service.delete_s3_object(storage_key=storage_result.storage_key, config=config)
        raise AppError(
            error_code="SNOWFLAKE_RAW_LOAD_FAILED",
            failed_step="snowflake_raw_load",
            message="MeshFlow could not load the CSV into Snowflake Warehouse Raw.",
            next_action="Check Snowflake stage, warehouse, schema, and COPY INTO permissions.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    dataset = Dataset(
        id=dataset_id,
        demo_session_id=check.session.id,
        name=check.csv.file.file_name,
        source_type="uploaded_csv",
        status="schema_review",
        raw_table_name=load_result.raw_table_name,
        storage_uri=storage_result.storage_uri,
        storage_key=storage_result.storage_key,
        row_count=load_result.rows_loaded,
        column_count=check.csv.file.column_count,
    )
    dataset_file = DatasetFile(
        dataset=dataset,
        file_name=check.csv.file.file_name,
        storage_key=storage_result.storage_key,
        file_size_bytes=check.csv.file.size_bytes,
        content_type=content_type,
        checksum_sha256=hashlib.sha256(check.csv.content).hexdigest(),
        row_count=len(check.csv.data_rows),
        column_count=check.csv.file.column_count,
    )
    profiles = build_column_profiles(check.csv, dataset_file)

    check.session.successful_uploads_used += 1
    check.session.uploaded_datasets_used += 1
    check.session.total_upload_mb_used = round(
        check.session.total_upload_mb_used + check.csv.file.size_mb,
        4,
    )

    db.add(dataset)
    db.add(dataset_file)
    db.add_all(profiles)
    db.commit()
    db.refresh(dataset)
    db.refresh(dataset_file)

    return DatasetUploadResponse(
        status="uploaded",
        dataset=dataset_summary(dataset),
        file=dataset_file_summary(dataset_file),
        schema_preview=schema_preview_from_profiles(dataset.column_profiles),
        next_route=f"/demo/data-flow?datasetId={dataset.id}",
    )


def list_datasets(
    db: Session,
    session_id: str | None,
) -> DatasetListResponse:
    session = get_required_session(db, session_id)
    datasets = db.scalars(
        select(Dataset)
        .where(Dataset.demo_session_id == session.id, Dataset.deleted_at.is_(None))
        .order_by(Dataset.created_at.desc())
    ).all()
    return DatasetListResponse(datasets=[dataset_summary(dataset) for dataset in datasets])


def get_dataset_detail(
    db: Session,
    session_id: str | None,
    dataset_id: str,
) -> DatasetDetailResponse:
    session = get_required_session(db, session_id)
    dataset = db.scalar(
        select(Dataset)
        .where(
            Dataset.id == dataset_id,
            Dataset.demo_session_id == session.id,
            Dataset.deleted_at.is_(None),
        )
        .options(selectinload(Dataset.files), selectinload(Dataset.column_profiles))
    )
    if dataset is None:
        raise AppError(
            error_code="DATASET_NOT_FOUND",
            failed_step="dataset",
            message="The requested dataset was not found for this demo session.",
            next_action="Select an available dataset from the workspace.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    dataset_file = dataset.files[0] if dataset.files else None
    return DatasetDetailResponse(
        dataset=dataset_summary(dataset),
        file=dataset_file_summary(dataset_file) if dataset_file else None,
        schema_preview=schema_preview_from_profiles(dataset.column_profiles),
    )


def get_dataset_profile(
    db: Session,
    session_id: str | None,
    dataset_id: str,
) -> SchemaPreview:
    return get_dataset_detail(db, session_id, dataset_id).schema_preview
