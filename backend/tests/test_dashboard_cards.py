import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.dataset import (
    AnalysisInsight,
    AnalysisRun,
    AnalysisRunChart,
    DashboardCard,
    Dataset,
    DatasetTransformationRun,
    utc_now,
)
from app.models.demo_session import DemoSession
from app.services import snowflake_service
from app.services.demo_session_service import DEMO_SESSION_HEADER, reset_demo_session
from app.services.semantic_preparation_service import ProviderCandidate


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def create_ready_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_dashboard_ready",
) -> Dataset:
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="Raw Retail Transactions Demo",
        source_type="demo_raw_retail",
        status="ready_for_analysis",
        raw_table_name="RAW_UPLOAD_DASHBOARD_TEST",
        storage_uri="s3://bucket/key",
        storage_key="key",
        row_count=4,
        column_count=18,
    )
    db_session.add(dataset)
    db_session.add(
        DatasetTransformationRun(
            dataset=dataset,
            status="completed",
            dbt_run_summary_json={
                "models": {
                    "data_marts": [
                        "mart_sales_performance",
                        "mart_product_performance",
                        "mart_customer_segments",
                        "mart_store_performance",
                    ]
                }
            },
        )
    )
    db_session.commit()
    return dataset


def create_analysis_with_chart(
    db_session: Session,
    session_id: str,
    *,
    analysis_id: str = "an_dashboard_ready",
    dataset_id: str = "ds_dashboard_ready",
    status: str = "completed",
    with_chart: bool = True,
    with_insight: bool = True,
) -> AnalysisRun:
    dataset = create_ready_dataset(db_session, session_id, dataset_id=dataset_id)
    run = AnalysisRun(
        id=analysis_id,
        demo_session_id=session_id,
        dataset=dataset,
        question="How is revenue performing?",
        normalized_question="how is revenue performing",
        status=status,
        decision_type="create_new",
        source_model="mart_sales_performance",
        grain="one row per month",
        metrics_json=[{"name": "revenue", "aggregation": "sum"}],
        dimensions_json=["order_month"],
        filters_json=[],
        generated_sql="SELECT ORDER_MONTH, SUM(REVENUE) AS REVENUE FROM MART_SALES_PERFORMANCE",
        output_schema_json=[
            {"name": "ORDER_MONTH", "type": "TEXT"},
            {"name": "REVENUE", "type": "FIXED"},
        ],
        preview_rows_json=[{"ORDER_MONTH": "2026-01", "REVENUE": "100.00"}],
        row_count=1,
        completed_at=utc_now() if status == "completed" else None,
    )
    db_session.add(run)
    if with_chart:
        chart = AnalysisRunChart(
            analysis_run=run,
            dataset_id=dataset.id,
            chart_type="line",
            title="Revenue Trend",
            description="Generated from stored Snowflake query output.",
            chart_spec_json={
                "type": "line",
                "title": "Revenue Trend",
                "x": {"field": "ORDER_MONTH", "label": "Month", "semantic_type": "time"},
                "y": {"field": "REVENUE", "label": "Revenue", "format": "currency"},
                "source_model": "mart_sales_performance",
            },
            data_json=[{"ORDER_MONTH": "2026-01", "REVENUE": "100.00"}],
            source_model="mart_sales_performance",
            metric_summary="REVENUE",
            dimension_summary="ORDER_MONTH",
            sort_order=0,
        )
        db_session.add(chart)
        if with_insight:
            db_session.add(
                AnalysisInsight(
                    analysis_run=run,
                    chart=chart,
                    insight_level="chart",
                    status="completed",
                    summary="Revenue is visible in the preview.",
                    key_findings_json=["The preview contains one revenue point."],
                    tags_json=["revenue"],
                    confidence="medium",
                    provider_name="gemini_model_1_key_1",
                    provider_model="gemini-model",
                )
            )
    db_session.commit()
    db_session.refresh(run)
    return run


def post_dashboard_card(client: TestClient, session_id: str | None, analysis_run_id: str):
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.post(
        "/api/v1/dashboard/cards",
        headers=headers,
        json={"analysis_run_id": analysis_run_id},
    )


def test_create_dashboard_card_requires_session_header(client: TestClient) -> None:
    response = post_dashboard_card(client, None, "an_missing")

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_create_dashboard_card_rejects_invalid_session(client: TestClient) -> None:
    response = post_dashboard_card(client, "mf_demo_missing", "an_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_create_dashboard_card_blocks_cross_session_analysis(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    run = create_analysis_with_chart(db_session, owner_session_id)

    response = post_dashboard_card(client, other_session_id, run.id)

    assert response.status_code == 404
    assert response.json()["error_code"] == "ANALYSIS_RUN_NOT_FOUND"


def test_create_dashboard_card_requires_completed_analysis(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    run = create_analysis_with_chart(db_session, session_id, status="running", with_chart=False)

    response = post_dashboard_card(client, session_id, run.id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "ANALYSIS_NOT_COMPLETED"


def test_create_dashboard_card_requires_real_charts(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    run = create_analysis_with_chart(db_session, session_id, with_chart=False)

    response = post_dashboard_card(client, session_id, run.id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "ANALYSIS_HAS_NO_CHARTS"


def test_successful_result_group_card_stores_snapshot_and_increments_usage(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    run = create_analysis_with_chart(db_session, session_id)

    response = post_dashboard_card(client, session_id, run.id)

    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["cards_used"] == 1
    snapshot = body["card"]["card_snapshot"]
    assert snapshot["dataset"]["name"] == "Raw Retail Transactions Demo"
    assert snapshot["charts"][0]["title"] == "Revenue Trend"
    assert snapshot["insights"][0]["summary"] == "Revenue is visible in the preview."
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).dashboard_cards_used == 1
    assert db_session.scalar(select(DashboardCard)).status == "active"


def test_delete_card_removes_visible_card_without_restoring_quota(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    run = create_analysis_with_chart(db_session, session_id)
    card_id = post_dashboard_card(client, session_id, run.id).json()["card"]["id"]

    delete_response = client.delete(
        f"/api/v1/dashboard/cards/{card_id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    dashboard_response = client.get(
        "/api/v1/dashboard",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["cards_used"] == 1
    assert dashboard_response.json()["cards"] == []
    db_session.expire_all()
    card = db_session.get(DashboardCard, card_id)
    assert card.status == "archived"
    assert db_session.get(DemoSession, session_id).dashboard_cards_used == 1


def test_reset_archives_visible_cards_without_restoring_quota_by_default(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    run = create_analysis_with_chart(db_session, session_id)
    post_dashboard_card(client, session_id, run.id)

    response = client.post(
        "/api/v1/demo-sessions/reset",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    workspace = client.get(
        "/api/v1/workspace",
        headers={DEMO_SESSION_HEADER: session_id},
    ).json()

    assert response.status_code == 200
    assert response.json()["usage"]["dashboard_cards_used"] == 1
    assert workspace["dashboard"]["cards"] == []
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).dashboard_cards_used == 1


def test_development_reset_can_reset_usage_when_configured(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    session = db_session.get(DemoSession, session_id)
    session.dashboard_cards_used = 3
    db_session.commit()

    response = reset_demo_session(
        db_session,
        session_id,
        Settings(ALLOW_DEMO_RESET_USAGE=True),
    )

    assert response.usage.dashboard_cards_used == 0


def test_dashboard_card_quota_blocks_ninth_card(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    session = db_session.get(DemoSession, session_id)
    session.dashboard_cards_used = 8
    db_session.commit()
    run = create_analysis_with_chart(db_session, session_id)

    response = post_dashboard_card(client, session_id, run.id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "DASHBOARD_CARD_LIMIT_REACHED"


def analysis_candidates() -> list[ProviderCandidate]:
    return [ProviderCandidate("openai_fallback", "openai", "openai-key", "openai-model")]


def plan_payload() -> str:
    return json.dumps(
        {
            "decision_type": "create_new",
            "question": "How is revenue performing?",
            "intent": "revenue_trend",
            "source_model": "mart_sales_performance",
            "grain": "one row per month",
            "metrics": [{"name": "revenue", "aggregation": "sum"}],
            "dimensions": ["order_month"],
            "filters": [],
            "sort": [{"field": "order_month", "direction": "asc"}],
            "limit": 100,
            "assumptions": [],
            "warnings": [],
        }
    )


def query_result() -> snowflake_service.SnowflakeQueryResult:
    return snowflake_service.SnowflakeQueryResult(
        output_schema=[
            {"name": "ORDER_MONTH", "type": "TEXT"},
            {"name": "REVENUE", "type": "FIXED"},
        ],
        preview_rows=[{"ORDER_MONTH": "2026-01", "REVENUE": "100.00"}],
        row_count=1,
    )


def patch_analysis_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: analysis_candidates(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: plan_payload(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.snowflake_service.execute_analysis_query",
        lambda **_kwargs: query_result(),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: [],
    )


def post_saved_analysis(client: TestClient, session_id: str, dataset_id: str):
    return client.post(
        "/api/v1/analysis-runs",
        headers={DEMO_SESSION_HEADER: session_id},
        json={
            "attached_dataset_id": dataset_id,
            "question": "How is revenue performing?",
            "save_to_dashboard": True,
        },
    )


def test_analysis_save_to_dashboard_checks_card_quota_before_expensive_work(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    session_id = create_session(client)
    dataset = create_ready_dataset(db_session, session_id)
    session = db_session.get(DemoSession, session_id)
    session.dashboard_cards_used = 8
    db_session.commit()
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("provider should not be called when card quota is exhausted")
        ),
    )

    response = post_saved_analysis(client, session_id, dataset.id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "DASHBOARD_CARD_LIMIT_REACHED"


def test_analysis_save_to_dashboard_creates_card_after_success(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    session_id = create_session(client)
    dataset = create_ready_dataset(db_session, session_id)

    response = post_saved_analysis(client, session_id, dataset.id)

    assert response.status_code == 200
    body = response.json()
    assert body["saved_dashboard_card"]["card_type"] == "result_group"
    assert body["dashboard_card_created"] is True
    assert body["saved_dashboard_card"]["card_snapshot"]["charts"]
    db_session.expire_all()
    session = db_session.get(DemoSession, session_id)
    assert session.successful_analysis_runs_used == 1
    assert session.dashboard_cards_used == 1


def test_reused_analysis_with_existing_card_returns_card_without_incrementing_quota(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    session_id = create_session(client)
    dataset = create_ready_dataset(db_session, session_id)
    first = post_saved_analysis(client, session_id, dataset.id).json()
    first_card_id = first["saved_dashboard_card"]["id"]

    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("provider should not be called for reuse")
        ),
    )
    second_response = post_saved_analysis(client, session_id, dataset.id)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["reused"] is True
    assert second["saved_dashboard_card"]["id"] == first_card_id
    assert second["dashboard_card_created"] is False
    db_session.expire_all()
    session = db_session.get(DemoSession, session_id)
    assert session.successful_analysis_runs_used == 1
    assert session.dashboard_cards_used == 1


def test_workspace_and_limits_reflect_persisted_cards_after_delete(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    run = create_analysis_with_chart(db_session, session_id)
    card_id = post_dashboard_card(client, session_id, run.id).json()["card"]["id"]

    workspace = client.get(
        "/api/v1/workspace",
        headers={DEMO_SESSION_HEADER: session_id},
    ).json()
    client.delete(
        f"/api/v1/dashboard/cards/{card_id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    limits = client.get("/api/v1/limits", headers={DEMO_SESSION_HEADER: session_id}).json()

    assert workspace["dashboard"]["cards"][0]["id"] == card_id
    assert workspace["dashboard"]["cards_used"] == 1
    assert limits["usage"]["dashboard_cards_used"] == 1
