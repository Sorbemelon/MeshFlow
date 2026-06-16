from __future__ import annotations

from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.core.errors import AppError
from app.models.dataset import AnalysisRun, DashboardCard
from app.models.dataset import utc_now as model_utc_now
from app.models.demo_session import DemoSession
from app.schemas.dashboard import (
    DashboardCardMutationResponse,
    DashboardCardSummary,
    DashboardResponse,
)
from app.services.demo_session_service import configured_limits, get_required_session


ACTIVE_CARD_STATUS = "active"
ARCHIVED_CARD_STATUS = "archived"
RESULT_GROUP_CARD_TYPE = "result_group"


def dashboard_card_summary(card: DashboardCard) -> DashboardCardSummary:
    return DashboardCardSummary(
        id=card.id,
        demo_session_id=card.demo_session_id,
        dataset_id=card.dataset_id,
        analysis_run_id=card.analysis_run_id,
        analysis_run_chart_id=card.analysis_run_chart_id,
        card_type=card.card_type,
        title=card.title,
        subtitle=card.subtitle,
        dataset_name_snapshot=card.dataset_name_snapshot,
        source_model_snapshot=card.source_model_snapshot,
        card_snapshot=card.card_snapshot_json,
        sort_order=card.sort_order,
        status=card.status,
        archived_at=card.archived_at.isoformat() if card.archived_at else None,
        created_at=card.created_at.isoformat(),
        updated_at=card.updated_at.isoformat(),
    )


def _card_quota_error(config: Settings = settings) -> AppError:
    limit = config.max_dashboard_cards_per_session
    return AppError(
        error_code="DASHBOARD_CARD_LIMIT_REACHED",
        failed_step="dashboard_card_quota",
        message=f"This demo session has already used the maximum of {limit} dashboard cards.",
        next_action=(
            "Resetting or deleting cards will not restore public quota. "
            "Start a new session after expiry or use fewer saved cards."
        ),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def ensure_dashboard_card_quota_available(
    session: DemoSession,
    config: Settings = settings,
) -> None:
    if session.dashboard_cards_used >= config.max_dashboard_cards_per_session:
        raise _card_quota_error(config)


def _analysis_not_completed_error() -> AppError:
    return AppError(
        error_code="ANALYSIS_NOT_COMPLETED",
        failed_step="dashboard_card_source",
        message="Dashboard cards can only be created from completed analysis runs.",
        next_action="Generate a completed analysis before saving it to the dashboard.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _analysis_has_no_charts_error() -> AppError:
    return AppError(
        error_code="ANALYSIS_HAS_NO_CHARTS",
        failed_step="dashboard_card_source",
        message="This completed analysis has no real chart snapshots to save.",
        next_action="Retry analysis generation and confirm ChartSpec generation succeeds.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _card_not_found_error() -> AppError:
    return AppError(
        error_code="DASHBOARD_CARD_NOT_FOUND",
        failed_step="dashboard_card",
        message="The requested dashboard card was not found for this demo session.",
        next_action="Refresh the dashboard and choose a visible card.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _load_analysis_run_for_card(
    db: Session,
    session_id: str,
    analysis_run_id: str,
) -> AnalysisRun:
    analysis_run = db.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.id == analysis_run_id,
            AnalysisRun.demo_session_id == session_id,
        )
        .options(
            selectinload(AnalysisRun.dataset),
            selectinload(AnalysisRun.charts),
            selectinload(AnalysisRun.insights),
            selectinload(AnalysisRun.provider_runs),
        )
    )
    if analysis_run is None:
        raise AppError(
            error_code="ANALYSIS_RUN_NOT_FOUND",
            failed_step="dashboard_card_source",
            message="The analysis run was not found for this demo session.",
            next_action="Select an analysis run from the current session.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return analysis_run


def _active_card_for_analysis(
    db: Session,
    session_id: str,
    analysis_run_id: str,
) -> DashboardCard | None:
    return db.scalar(
        select(DashboardCard)
        .where(
            DashboardCard.demo_session_id == session_id,
            DashboardCard.analysis_run_id == analysis_run_id,
            DashboardCard.card_type == RESULT_GROUP_CARD_TYPE,
            DashboardCard.status == ACTIVE_CARD_STATUS,
        )
        .order_by(DashboardCard.created_at.asc())
    )


def _active_cards_statement(session_id: str):
    return (
        select(DashboardCard)
        .where(
            DashboardCard.demo_session_id == session_id,
            DashboardCard.status == ACTIVE_CARD_STATUS,
        )
        .order_by(DashboardCard.sort_order.asc(), DashboardCard.created_at.asc())
    )


def active_dashboard_cards_for_session(db: Session, session_id: str) -> list[DashboardCard]:
    return list(db.scalars(_active_cards_statement(session_id)).all())


def _next_sort_order(db: Session, session_id: str) -> int:
    max_order = db.scalar(
        select(func.max(DashboardCard.sort_order)).where(
            DashboardCard.demo_session_id == session_id,
            DashboardCard.status == ACTIVE_CARD_STATUS,
        )
    )
    return int(max_order or 0) + 1


def _chart_snapshot(chart) -> dict[str, Any]:
    return {
        "id": chart.id,
        "analysis_run_id": chart.analysis_run_id,
        "dataset_id": chart.dataset_id,
        "chart_type": chart.chart_type,
        "title": chart.title,
        "description": chart.description,
        "chart_spec": chart.chart_spec_json,
        "data": chart.data_json,
        "source_model": chart.source_model,
        "metric_summary": chart.metric_summary,
        "dimension_summary": chart.dimension_summary,
        "sort_order": chart.sort_order,
        "created_at": chart.created_at.isoformat(),
    }


def _insight_snapshot(insight) -> dict[str, Any]:
    return {
        "id": insight.id,
        "analysis_run_id": insight.analysis_run_id,
        "analysis_run_chart_id": insight.analysis_run_chart_id,
        "insight_level": insight.insight_level,
        "status": insight.status,
        "summary": insight.summary,
        "key_findings": insight.key_findings_json or [],
        "tags": insight.tags_json or [],
        "confidence": insight.confidence,
        "provider_name": insight.provider_name,
        "provider_model": insight.provider_model,
        "error_code": insight.error_code,
        "error_message": insight.error_message,
        "created_at": insight.created_at.isoformat(),
        "updated_at": insight.updated_at.isoformat(),
    }


def _provider_snapshot(provider_run) -> dict[str, Any]:
    return {
        "task_type": provider_run.task_type,
        "provider_name": provider_run.provider_name,
        "provider_model": provider_run.provider_model,
        "status": provider_run.status,
        "error_code": provider_run.error_code,
        "fallback_from_provider": provider_run.fallback_from_provider,
    }


def build_result_group_snapshot(analysis_run: AnalysisRun) -> dict[str, Any]:
    dataset = analysis_run.dataset
    return {
        "snapshot_version": 1,
        "dataset": {
            "id": analysis_run.dataset_id,
            "name": dataset.name if dataset else None,
            "source_type": dataset.source_type if dataset else None,
        },
        "analysis_run": {
            "id": analysis_run.id,
            "question": analysis_run.question,
            "status": analysis_run.status,
            "decision_type": analysis_run.decision_type,
            "source_model": analysis_run.source_model,
            "grain": analysis_run.grain,
            "metrics": analysis_run.metrics_json or [],
            "dimensions": analysis_run.dimensions_json or [],
            "row_count": analysis_run.row_count,
            "completed_at": analysis_run.completed_at.isoformat()
            if analysis_run.completed_at
            else None,
        },
        "charts": [_chart_snapshot(chart) for chart in analysis_run.charts],
        "insights": [_insight_snapshot(insight) for insight in analysis_run.insights],
        "provider_runs": [
            _provider_snapshot(provider_run)
            for provider_run in analysis_run.provider_runs
            if provider_run.task_type in {"analysis_plan", "insight_generation"}
        ],
        "generated_at": model_utc_now().isoformat(),
    }


def validate_analysis_for_dashboard_card(analysis_run: AnalysisRun) -> None:
    if analysis_run.status != "completed":
        raise _analysis_not_completed_error()
    if not analysis_run.charts:
        raise _analysis_has_no_charts_error()


def ensure_dashboard_card_for_analysis(
    db: Session,
    session: DemoSession,
    analysis_run: AnalysisRun,
    config: Settings = settings,
) -> tuple[DashboardCard, bool]:
    existing = _active_card_for_analysis(db, session.id, analysis_run.id)
    if existing is not None:
        return existing, False

    validate_analysis_for_dashboard_card(analysis_run)
    ensure_dashboard_card_quota_available(session, config)
    snapshot = build_result_group_snapshot(analysis_run)
    dataset_name = snapshot["dataset"].get("name") if isinstance(snapshot["dataset"], dict) else None
    card = DashboardCard(
        demo_session_id=session.id,
        dataset_id=analysis_run.dataset_id,
        analysis_run=analysis_run,
        card_type=RESULT_GROUP_CARD_TYPE,
        title=analysis_run.question,
        subtitle=analysis_run.source_model,
        dataset_name_snapshot=dataset_name if isinstance(dataset_name, str) else None,
        source_model_snapshot=analysis_run.source_model,
        card_snapshot_json=snapshot,
        sort_order=_next_sort_order(db, session.id),
        status=ACTIVE_CARD_STATUS,
    )
    db.add(card)
    db.flush()
    session.dashboard_cards_used += 1
    db.flush()
    return card, True


def create_dashboard_card_from_analysis_run(
    db: Session,
    session_id: str | None,
    analysis_run_id: str,
    config: Settings = settings,
) -> DashboardCardMutationResponse:
    session = get_required_session(db, session_id)
    analysis_run = _load_analysis_run_for_card(db, session.id, analysis_run_id)
    card, created = ensure_dashboard_card_for_analysis(db, session, analysis_run, config)
    db.commit()
    db.refresh(card)
    return DashboardCardMutationResponse(
        card=dashboard_card_summary(card),
        cards_used=session.dashboard_cards_used,
        cards_limit=configured_limits(config).max_dashboard_cards_per_session,
        created=created,
        message=(
            "Dashboard card saved."
            if created
            else "This analysis is already visible on the dashboard."
        ),
    )


def get_dashboard_response(
    db: Session,
    session_id: str | None,
    config: Settings = settings,
) -> DashboardResponse:
    session = get_required_session(db, session_id)
    limits = configured_limits(config)
    cards = active_dashboard_cards_for_session(db, session.id)
    return DashboardResponse(
        dashboard_count=limits.dashboards_per_session,
        cards=[dashboard_card_summary(card) for card in cards],
        cards_used=session.dashboard_cards_used,
        cards_limit=limits.max_dashboard_cards_per_session,
        visible_card_count=len(cards),
    )


def archive_dashboard_card(
    db: Session,
    session_id: str | None,
    card_id: str,
    config: Settings = settings,
) -> DashboardCardMutationResponse:
    session = get_required_session(db, session_id)
    card = db.scalar(
        select(DashboardCard).where(
            DashboardCard.id == card_id,
            DashboardCard.demo_session_id == session.id,
        )
    )
    if card is None:
        raise _card_not_found_error()
    if card.status == ACTIVE_CARD_STATUS:
        card.status = ARCHIVED_CARD_STATUS
        card.archived_at = model_utc_now()
        db.flush()
    db.commit()
    db.refresh(card)
    return DashboardCardMutationResponse(
        card=dashboard_card_summary(card),
        cards_used=session.dashboard_cards_used,
        cards_limit=configured_limits(config).max_dashboard_cards_per_session,
        created=False,
        message="Dashboard card removed from the visible canvas. Public quota was not restored.",
    )


def archive_active_dashboard_cards(db: Session, session_id: str) -> int:
    cards = active_dashboard_cards_for_session(db, session_id)
    archived_at = model_utc_now()
    for card in cards:
        card.status = ARCHIVED_CARD_STATUS
        card.archived_at = archived_at
    if cards:
        db.flush()
    return len(cards)
