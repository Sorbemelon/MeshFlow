from datetime import UTC, datetime, timedelta

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
from app.services import dbt_transformation_service, snowflake_service, storage_service
from app.services.cleanup_service import cleanup_dataset_external_resources
from app.services.demo_session_service import DEMO_SESSION_HEADER, mark_expired_sessions


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def create_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_lifecycle",
    status: str = "ready_for_analysis",
) -> Dataset:
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="Raw Retail Transactions Demo",
        source_type="demo_raw_retail",
        status=status,
        raw_table_name="RAW_UPLOAD_LIFECYCLE",
        storage_uri="s3://bucket/sessions/session/raw/ds_lifecycle/file.csv",
        storage_key="sessions/session/raw/ds_lifecycle/file.csv",
        row_count=2,
        column_count=3,
    )
    db_session.add(dataset)
    db_session.add(
        DatasetTransformationRun(
            dataset=dataset,
            status="completed",
            dbt_run_summary_json={
                "models": {"data_marts": ["mart_sales_performance"]},
            },
        )
    )
    db_session.commit()
    db_session.refresh(dataset)
    return dataset


def create_analysis_with_chart(
    db_session: Session,
    session_id: str,
    dataset: Dataset,
    *,
    analysis_id: str = "an_lifecycle",
) -> AnalysisRun:
    run = AnalysisRun(
        id=analysis_id,
        demo_session_id=session_id,
        dataset=dataset,
        question="How is revenue performing?",
        normalized_question="how is revenue performing",
        status="completed",
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
        completed_at=utc_now(),
    )
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
    db_session.add(run)
    db_session.add(chart)
    db_session.add(
        AnalysisInsight(
            analysis_run=run,
            chart=chart,
            insight_level="question",
            status="completed",
            summary="Revenue appears in the stored preview.",
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


def create_dashboard_card(client: TestClient, session_id: str, analysis_run_id: str) -> str:
    response = client.post(
        "/api/v1/dashboard/cards",
        headers={DEMO_SESSION_HEADER: session_id},
        json={"analysis_run_id": analysis_run_id},
    )
    assert response.status_code == 200
    return response.json()["card"]["id"]


def delete_dataset(client: TestClient, session_id: str | None, dataset_id: str):
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)


def test_delete_dataset_requires_session_header(client: TestClient) -> None:
    response = delete_dataset(client, None, "ds_missing")

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_delete_dataset_rejects_invalid_session(client: TestClient) -> None:
    response = delete_dataset(client, "mf_demo_missing", "ds_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_delete_dataset_rejects_cross_session_dataset(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset = create_dataset(db_session, owner_session_id)

    response = delete_dataset(client, other_session_id, dataset.id)

    assert response.status_code == 404
    assert response.json()["error_code"] == "DATASET_NOT_FOUND"


def test_delete_dataset_rejects_missing_dataset(client: TestClient) -> None:
    session_id = create_session(client)

    response = delete_dataset(client, session_id, "ds_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "DATASET_NOT_FOUND"


def test_delete_dataset_soft_deletes_and_excludes_active_workspace(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        storage_service,
        "delete_s3_object_for_cleanup",
        lambda **_kwargs: storage_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        snowflake_service,
        "drop_raw_table_for_cleanup",
        lambda **_kwargs: snowflake_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        dbt_transformation_service,
        "cleanup_dataset_runtime_artifacts",
        lambda **_kwargs: dbt_transformation_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        dbt_transformation_service,
        "cleanup_dataset_model_tables",
        lambda **_kwargs: dbt_transformation_service.CleanupOperationResult(status="completed"),
    )
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)

    response = delete_dataset(client, session_id, dataset.id)
    workspace = client.get("/api/v1/workspace", headers={DEMO_SESSION_HEADER: session_id})

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert response.json()["quota_restored"] is False
    assert response.json()["cleanup"] == {
        "s3": "completed",
        "snowflake": "completed",
        "dbt_runtime": "completed",
        "warnings": [],
    }
    assert workspace.json()["datasets"] == []
    assert workspace.json()["ready_datasets"] == []
    db_session.expire_all()
    deleted_dataset = db_session.get(Dataset, dataset.id)
    assert deleted_dataset.status == "deleted"
    assert deleted_dataset.deleted_at is not None


def test_delete_dataset_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)
    delete_dataset(client, session_id, dataset.id)

    response = delete_dataset(client, session_id, dataset.id)

    assert response.status_code == 200
    assert response.json()["status"] == "already_deleted"


def test_delete_dataset_preserves_history_and_dashboard_snapshots(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)
    run = create_analysis_with_chart(db_session, session_id, dataset)
    card_id = create_dashboard_card(client, session_id, run.id)

    response = delete_dataset(client, session_id, dataset.id)
    history = client.get("/api/v1/analysis-runs", headers={DEMO_SESSION_HEADER: session_id})
    detail = client.get(
        f"/api/v1/analysis-runs/{run.id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    dashboard = client.get("/api/v1/dashboard", headers={DEMO_SESSION_HEADER: session_id})

    assert response.status_code == 200
    assert history.json()["analysis_runs"][0]["dataset_deleted"] is True
    assert detail.json()["analysis_run"]["dataset_deleted"] is True
    card = dashboard.json()["cards"][0]
    assert card["id"] == card_id
    assert card["source_dataset_deleted"] is True
    assert card["card_snapshot"]["dataset"]["deleted"] is True
    assert card["card_snapshot"]["charts"][0]["title"] == "Revenue Trend"


def test_delete_dataset_does_not_decrement_usage(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)
    session = db_session.get(DemoSession, session_id)
    session.demo_dataset_used = 1
    session.uploaded_datasets_used = 1
    session.successful_analysis_runs_used = 3
    session.dashboard_cards_used = 2
    db_session.commit()

    response = delete_dataset(client, session_id, dataset.id)
    limits = client.get("/api/v1/limits", headers={DEMO_SESSION_HEADER: session_id}).json()

    assert response.status_code == 200
    assert limits["usage"]["demo_dataset_used"] == 1
    assert limits["usage"]["uploaded_datasets_used"] == 1
    assert limits["usage"]["successful_analysis_runs_used"] == 3
    assert limits["usage"]["dashboard_cards_used"] == 2


def test_cleanup_dataset_external_resources_drops_recorded_dbt_model_tables(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    dropped_models: list[str] = []
    monkeypatch.setattr(
        storage_service,
        "delete_s3_object_for_cleanup",
        lambda **_kwargs: storage_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        snowflake_service,
        "drop_raw_table_for_cleanup",
        lambda **_kwargs: snowflake_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        snowflake_service,
        "drop_tables_for_cleanup",
        lambda table_names, **_kwargs: dropped_models.extend(table_names)
        or snowflake_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        dbt_transformation_service,
        "cleanup_dataset_runtime_artifacts",
        lambda **_kwargs: dbt_transformation_service.CleanupOperationResult(status="completed"),
    )
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)

    cleanup = cleanup_dataset_external_resources(dataset)

    assert cleanup.snowflake == "completed"
    assert cleanup.warnings == []
    assert dropped_models == ["mart_sales_performance"]


def test_deleted_dataset_blocks_semantic_transform_and_new_analysis(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)
    delete_dataset(client, session_id, dataset.id)

    semantic = client.post(
        f"/api/v1/datasets/{dataset.id}/semantic-preparation",
        headers={DEMO_SESSION_HEADER: session_id},
        json={"force": True},
    )
    transform = client.post(
        f"/api/v1/datasets/{dataset.id}/transform",
        headers={DEMO_SESSION_HEADER: session_id},
        json={"force": True},
    )
    analysis = client.post(
        "/api/v1/analysis-runs",
        headers={DEMO_SESSION_HEADER: session_id},
        json={"attached_dataset_id": dataset.id, "question": "How is revenue performing?"},
    )

    assert semantic.status_code == 410
    assert transform.status_code == 410
    assert analysis.status_code == 410
    assert semantic.json()["error_code"] == "DATASET_DELETED"
    assert transform.json()["error_code"] == "DATASET_DELETED"
    assert analysis.json()["error_code"] == "DATASET_DELETED"


def test_reset_clears_visible_workspace_without_restoring_usage(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset = create_dataset(db_session, session_id)
    run = create_analysis_with_chart(db_session, session_id, dataset)
    create_dashboard_card(client, session_id, run.id)
    session = db_session.get(DemoSession, session_id)
    session.demo_dataset_used = 1
    session.successful_analysis_runs_used = 1
    db_session.commit()

    response = client.post(
        "/api/v1/demo-sessions/reset",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    workspace = client.get("/api/v1/workspace", headers={DEMO_SESSION_HEADER: session_id})
    history = client.get("/api/v1/analysis-runs", headers={DEMO_SESSION_HEADER: session_id})
    detail = client.get(
        f"/api/v1/analysis-runs/{run.id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["workspace_cleared"] is True
    assert body["usage_reset"] is False
    assert body["quota_restored"] is False
    assert body["usage"]["demo_dataset_used"] == 1
    assert body["usage"]["successful_analysis_runs_used"] == 1
    assert workspace.json()["datasets"] == []
    assert workspace.json()["dashboard"]["cards"] == []
    assert workspace.json()["history"]["analysis_runs"] == []
    assert history.json()["analysis_runs"] == []
    assert detail.status_code == 404
    db_session.expire_all()
    card = db_session.scalar(select(DashboardCard))
    assert card.status == "archived"
    assert db_session.get(Dataset, dataset.id).status == "deleted"


def test_reset_reports_partial_external_cleanup_failure(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        storage_service,
        "delete_s3_object_for_cleanup",
        lambda **_kwargs: storage_service.CleanupOperationResult(
            status="failed",
            warning="S3 cleanup failed for object key test: ClientError.",
        ),
    )
    monkeypatch.setattr(
        snowflake_service,
        "drop_raw_table_for_cleanup",
        lambda **_kwargs: snowflake_service.CleanupOperationResult(
            status="not_configured",
            warning="Snowflake cleanup skipped because Snowflake is not configured.",
        ),
    )
    session_id = create_session(client)
    create_dataset(db_session, session_id)

    response = client.post(
        "/api/v1/demo-sessions/reset",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    cleanup = response.json()["cleanup"]
    assert cleanup["s3"] == "failed"
    assert cleanup["snowflake"] == "not_configured"
    assert cleanup["warnings"]


def test_development_reset_can_reset_usage_when_configured(db_session: Session) -> None:
    now = datetime.now(UTC)
    session = DemoSession(
        status="active",
        created_at=now,
        expires_at=now + timedelta(days=3),
        last_seen_at=now,
    )
    session.dashboard_cards_used = 4
    db_session.add(session)
    db_session.commit()

    from app.services.demo_session_service import reset_demo_session

    response = reset_demo_session(db_session, session.id, Settings(ALLOW_DEMO_RESET_USAGE=True))

    assert response.usage_reset is True
    assert response.quota_restored is True
    assert response.usage.dashboard_cards_used == 0


def test_expired_session_cleanup_marks_workspace_metadata_deleted(
    db_session: Session,
    monkeypatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        storage_service,
        "delete_s3_object_for_cleanup",
        lambda **_kwargs: calls.append("s3")
        or storage_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        snowflake_service,
        "drop_raw_table_for_cleanup",
        lambda **_kwargs: calls.append("snowflake")
        or snowflake_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        dbt_transformation_service,
        "cleanup_dataset_model_tables",
        lambda **_kwargs: calls.append("dbt_models")
        or dbt_transformation_service.CleanupOperationResult(status="completed"),
    )
    monkeypatch.setattr(
        dbt_transformation_service,
        "cleanup_dataset_runtime_artifacts",
        lambda **_kwargs: calls.append("dbt")
        or dbt_transformation_service.CleanupOperationResult(status="completed"),
    )
    now = datetime.now(UTC)
    session = DemoSession(
        status="active",
        created_at=now - timedelta(days=4),
        expires_at=now - timedelta(minutes=1),
        last_seen_at=now - timedelta(days=1),
    )
    db_session.add(session)
    db_session.commit()
    dataset = create_dataset(db_session, session.id)

    expired_count = mark_expired_sessions(db_session, now)

    assert expired_count == 1
    assert calls == ["s3", "snowflake", "dbt_models", "dbt"]
    db_session.expire_all()
    assert db_session.get(DemoSession, session.id).status == "expired"
    assert db_session.get(Dataset, dataset.id).status == "deleted"


def test_missing_external_config_is_reported_as_skipped_not_fake_success(
    db_session: Session,
) -> None:
    session_id = "mf_demo_cleanup_config"
    now = datetime.now(UTC)
    db_session.add(
        DemoSession(
            id=session_id,
            status="active",
            created_at=now,
            expires_at=now + timedelta(days=3),
            last_seen_at=now,
        )
    )
    db_session.commit()
    dataset = create_dataset(db_session, session_id)

    cleanup = cleanup_dataset_external_resources(
        dataset,
        Settings(
            _env_file=None,
            AWS_REGION=None,
            S3_BUCKET_NAME=None,
            AWS_ACCESS_KEY_ID=None,
            AWS_SECRET_ACCESS_KEY=None,
            SNOWFLAKE_ACCOUNT=None,
            SNOWFLAKE_USER=None,
            SNOWFLAKE_PASSWORD=None,
            SNOWFLAKE_ROLE=None,
            SNOWFLAKE_WAREHOUSE=None,
            SNOWFLAKE_DATABASE=None,
            SNOWFLAKE_SCHEMA=None,
            SNOWFLAKE_STAGE_NAME=None,
        ),
    )

    assert cleanup.s3 == "not_configured"
    assert cleanup.snowflake == "not_configured"
    assert cleanup.dbt_runtime == "skipped"
    assert cleanup.warnings
