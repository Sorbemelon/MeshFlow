from datetime import UTC, datetime, timedelta

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.core.errors import AppError
from app.models.dataset import AnalysisRun, Dataset
from app.models.demo_session import DemoSession
from app.schemas.dataset import DatasetSummary
from app.schemas.demo_session import (
    DemoSessionResetResponse,
    DemoSessionResponse,
    DemoSessionSummary,
)
from app.schemas.limits import DemoLimits, DemoUsage, LimitsResponse
from app.schemas.workspace import (
    DashboardSummary,
    HistorySummary,
    WorkspaceResponse,
    WorkspaceSetupStatus,
)


DEMO_SESSION_HEADER = "X-Demo-Session-Id"
ACTIVE_SESSION_STATUSES = {"active", "reset"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def configured_limits(config: Settings = settings) -> DemoLimits:
    return DemoLimits(
        retention_days=config.demo_session_retention_days,
        max_upload_file_size_mb=config.max_upload_file_size_mb,
        max_total_upload_size_mb=config.max_total_upload_size_mb,
        max_successful_analysis_runs_per_session=(
            config.max_successful_analysis_runs_per_session
        ),
        max_dashboard_cards_per_session=config.max_dashboard_cards_per_session,
        max_charts_per_analysis=config.max_charts_per_analysis,
        dashboards_per_session=config.dashboards_per_session,
    )


def usage_from_session(session: DemoSession) -> DemoUsage:
    return DemoUsage(
        successful_uploads_used=session.successful_uploads_used,
        uploaded_datasets_used=session.uploaded_datasets_used,
        successful_analysis_runs_used=session.successful_analysis_runs_used,
        dashboard_cards_used=session.dashboard_cards_used,
        total_upload_mb_used=session.total_upload_mb_used,
    )


def summary_from_session(
    session: DemoSession,
    config: Settings = settings,
) -> DemoSessionSummary:
    return DemoSessionSummary(
        id=session.id,
        status=session.status,
        created_at=as_utc(session.created_at),
        expires_at=as_utc(session.expires_at),
        retention_days=config.demo_session_retention_days,
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
        deleted_at=dataset.deleted_at.isoformat() if dataset.deleted_at else None,
    )


def analysis_history_summary(run: AnalysisRun) -> dict[str, object]:
    insight_status = "not_started"
    if any(insight.status == "completed" for insight in run.insights):
        insight_status = "completed"
    elif any(insight.status == "failed" for insight in run.insights):
        insight_status = "failed"

    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "dataset_name": run.dataset.name if run.dataset else None,
        "dataset_deleted": bool(
            run.dataset is None
            or run.dataset.deleted_at is not None
            or run.dataset.status == "deleted"
        ),
        "question": run.question,
        "status": run.status,
        "decision_type": run.decision_type,
        "source_model": run.source_model,
        "chart_count": len(run.charts),
        "insight_status": insight_status,
        "row_count": run.row_count,
        "error_code": run.error_code,
        "failed_step": run.failed_step,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def mark_expired_sessions(
    db: Session,
    now: datetime | None = None,
    config: Settings = settings,
) -> int:
    checked_at = now or utc_now()
    expired_count = 0
    sessions = db.scalars(
        select(DemoSession).where(DemoSession.status.in_(ACTIVE_SESSION_STATUSES))
    ).all()

    for session in sessions:
        if as_utc(session.expires_at) <= checked_at:
            from app.services.cleanup_service import clear_session_workspace

            clear_session_workspace(db, session, config)
            session.status = "expired"
            expired_count += 1

    if expired_count:
        db.commit()

    return expired_count


def create_demo_session(
    db: Session,
    config: Settings = settings,
    now: datetime | None = None,
) -> DemoSessionResponse:
    created_at = now or utc_now()
    mark_expired_sessions(db, created_at)

    session = DemoSession(
        status="active",
        created_at=created_at,
        expires_at=created_at + timedelta(days=config.demo_session_retention_days),
        last_seen_at=created_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DemoSessionResponse(
        session=summary_from_session(session, config),
        limits=configured_limits(config),
        usage=usage_from_session(session),
    )


def _session_required_error() -> AppError:
    return AppError(
        error_code="SESSION_ID_REQUIRED",
        failed_step="demo_session",
        message="The X-Demo-Session-Id header is required for this workspace request.",
        next_action="Start a new demo session and retry with the returned session id.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _session_not_found_error() -> AppError:
    return AppError(
        error_code="SESSION_NOT_FOUND",
        failed_step="demo_session",
        message="This anonymous demo session was not found.",
        next_action="Start a new demo session.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _session_expired_error() -> AppError:
    return AppError(
        error_code="SESSION_EXPIRED",
        failed_step="demo_session",
        message="This anonymous demo session has expired.",
        next_action="Start a new demo session.",
        status_code=status.HTTP_410_GONE,
    )


def get_required_session(
    db: Session,
    session_id: str | None,
    now: datetime | None = None,
) -> DemoSession:
    checked_at = now or utc_now()
    if not session_id:
        raise _session_required_error()

    session = db.get(DemoSession, session_id)
    if session is None:
        raise _session_not_found_error()

    if session.status == "expired" or as_utc(session.expires_at) <= checked_at:
        from app.services.cleanup_service import clear_session_workspace

        clear_session_workspace(db, session, settings)
        session.status = "expired"
        db.commit()
        raise _session_expired_error()

    if session.status not in ACTIVE_SESSION_STATUSES:
        raise _session_expired_error()

    session.last_seen_at = checked_at
    db.commit()
    db.refresh(session)
    return session


def get_current_session_response(
    db: Session,
    session_id: str | None,
    config: Settings = settings,
) -> DemoSessionResponse:
    session = get_required_session(db, session_id)
    return DemoSessionResponse(
        session=summary_from_session(session, config),
        limits=configured_limits(config),
        usage=usage_from_session(session),
    )


def reset_demo_session(
    db: Session,
    session_id: str | None,
    config: Settings = settings,
) -> DemoSessionResetResponse:
    session = get_required_session(db, session_id)
    session.status = "active"
    session.reset_at = utc_now()

    from app.services.cleanup_service import clear_session_workspace

    cleanup = clear_session_workspace(db, session, config)

    usage_reset = False

    db.commit()
    db.refresh(session)

    message = "Workspace was reset. Public demo quota usage was preserved."

    return DemoSessionResetResponse(
        status="reset",
        session=summary_from_session(session, config),
        limits=configured_limits(config),
        usage=usage_from_session(session),
        usage_reset=usage_reset,
        workspace_cleared=True,
        quota_restored=usage_reset,
        cleanup=cleanup,
        message=message,
        next_action="Launch a new workspace flow.",
    )


def get_limits_response(
    db: Session,
    session_id: str | None,
    config: Settings = settings,
) -> LimitsResponse:
    if not session_id:
        return LimitsResponse(limits=configured_limits(config), usage=None)

    session = get_required_session(db, session_id)
    return LimitsResponse(limits=configured_limits(config), usage=usage_from_session(session))


def get_workspace_response(
    db: Session,
    session_id: str | None,
    config: Settings = settings,
) -> WorkspaceResponse:
    session = get_required_session(db, session_id)
    limits = configured_limits(config)
    usage = usage_from_session(session)
    datasets = db.scalars(
        select(Dataset)
        .where(Dataset.demo_session_id == session.id, Dataset.deleted_at.is_(None))
        .order_by(Dataset.created_at.desc())
    ).all()
    ready_datasets = [
        dataset for dataset in datasets if dataset.status == "ready_for_analysis"
    ]
    analysis_runs = db.scalars(
        select(AnalysisRun)
        .where(
            AnalysisRun.demo_session_id == session.id,
            *(
                [AnalysisRun.created_at > session.reset_at]
                if session.reset_at is not None
                else []
            ),
        )
        .options(
            selectinload(AnalysisRun.dataset),
            selectinload(AnalysisRun.charts),
            selectinload(AnalysisRun.insights),
        )
        .order_by(AnalysisRun.created_at.desc())
        .limit(10)
    ).all()
    from app.services.dashboard_service import (
        active_dashboard_cards_for_session,
        dashboard_card_summary,
    )

    dashboard_cards = active_dashboard_cards_for_session(db, session.id)

    return WorkspaceResponse(
        session=summary_from_session(session, config),
        datasets=[dataset_summary(dataset) for dataset in datasets],
        ready_datasets=[dataset_summary(dataset) for dataset in ready_datasets],
        active_dataset=None,
        dashboard=DashboardSummary(
            dashboard_count=limits.dashboards_per_session,
            cards=[dashboard_card_summary(card) for card in dashboard_cards],
            cards_used=usage.dashboard_cards_used,
            cards_limit=limits.max_dashboard_cards_per_session,
            visible_card_count=len(dashboard_cards),
        ),
        history=HistorySummary(
            analysis_runs=[analysis_history_summary(run) for run in analysis_runs],
            successful_analysis_runs_used=usage.successful_analysis_runs_used,
            successful_analysis_runs_limit=(
                limits.max_successful_analysis_runs_per_session
            ),
        ),
        limits=limits,
        setup_status=WorkspaceSetupStatus(
            backend="available",
            storage="not_checked",
            warehouse="not_checked",
            dbt="not_checked",
            ai="not_checked",
        ),
    )
