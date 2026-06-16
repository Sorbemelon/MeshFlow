from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.models.dataset import DashboardCard, Dataset
from app.models.dataset import utc_now as model_utc_now
from app.models.demo_session import DemoSession
from app.schemas.dataset import CleanupSummary
from app.services import snowflake_service, storage_service
from app.services.dashboard_service import archive_active_dashboard_cards


def _status_rank(status: str) -> int:
    order = {"skipped": 0, "not_configured": 1, "completed": 2, "failed": 3}
    return order.get(status, 0)


def _merge_status(current: str, next_status: str) -> str:
    return next_status if _status_rank(next_status) > _status_rank(current) else current


def _combined_summary(summaries: Iterable[CleanupSummary]) -> CleanupSummary:
    combined = CleanupSummary()
    for summary in summaries:
        combined.s3 = _merge_status(combined.s3, summary.s3)
        combined.snowflake = _merge_status(combined.snowflake, summary.snowflake)
        combined.dbt_runtime = _merge_status(combined.dbt_runtime, summary.dbt_runtime)
        combined.warnings.extend(summary.warnings)
    return combined


def _warning_list(*warnings: str | None) -> list[str]:
    return [warning for warning in warnings if warning]


def _mark_dashboard_snapshots_dataset_deleted(
    db: Session,
    dataset: Dataset,
    deleted_at: datetime,
) -> None:
    cards = db.scalars(
        select(DashboardCard).where(DashboardCard.dataset_id == dataset.id)
    ).all()
    deleted_at_value = deleted_at.isoformat()
    for card in cards:
        snapshot = dict(card.card_snapshot_json or {})
        dataset_snapshot = dict(snapshot.get("dataset") or {})
        dataset_snapshot["deleted"] = True
        dataset_snapshot["deleted_at"] = deleted_at_value
        snapshot["dataset"] = dataset_snapshot
        card.card_snapshot_json = snapshot


def cleanup_dataset_external_resources(
    dataset: Dataset,
    config: Settings = settings,
) -> CleanupSummary:
    from app.services import dbt_transformation_service

    s3_result = storage_service.delete_s3_object_for_cleanup(
        storage_key=dataset.storage_key,
        config=config,
    )
    snowflake_result = snowflake_service.drop_raw_table_for_cleanup(
        raw_table_name=dataset.raw_table_name,
        config=config,
    )
    dbt_model_result = dbt_transformation_service.cleanup_dataset_model_tables(
        dataset=dataset,
        config=config,
    )
    dbt_result = dbt_transformation_service.cleanup_dataset_runtime_artifacts(
        dataset_id=dataset.id,
        config=config,
    )
    warnings = _warning_list(
        s3_result.warning,
        snowflake_result.warning,
        dbt_model_result.warning,
        dbt_result.warning,
    )
    return CleanupSummary(
        s3=s3_result.status,
        snowflake=_merge_status(snowflake_result.status, dbt_model_result.status),
        dbt_runtime=dbt_result.status,
        warnings=warnings,
    )


def soft_delete_dataset(
    db: Session,
    dataset: Dataset,
    config: Settings = settings,
) -> tuple[str, CleanupSummary]:
    if dataset.deleted_at is not None or dataset.status == "deleted":
        return "already_deleted", CleanupSummary()

    cleanup = cleanup_dataset_external_resources(dataset, config)
    deleted_at = model_utc_now()
    dataset.deleted_at = deleted_at
    dataset.status = "deleted"
    _mark_dashboard_snapshots_dataset_deleted(db, dataset, deleted_at)
    db.flush()
    return "deleted", cleanup


def clear_session_workspace(
    db: Session,
    session: DemoSession,
    config: Settings = settings,
) -> CleanupSummary:
    datasets = db.scalars(
        select(Dataset)
        .where(Dataset.demo_session_id == session.id, Dataset.deleted_at.is_(None))
        .options(selectinload(Dataset.files))
    ).all()
    cleanup_summaries = [
        soft_delete_dataset(db, dataset, config)[1]
        for dataset in datasets
    ]
    archive_active_dashboard_cards(db, session.id)
    if cleanup_summaries:
        return _combined_summary(cleanup_summaries)
    return CleanupSummary()
