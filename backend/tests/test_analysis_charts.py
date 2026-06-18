import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import AnalysisRun, AnalysisRunChart, Dataset, DatasetTransformationRun
from app.models.demo_session import DemoSession
from app.services import snowflake_service
from app.services.chartspec_service import ChartSpecError, validate_chart_spec
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.semantic_preparation_service import ProviderCandidate


@pytest.fixture(autouse=True)
def disable_insight_generation(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: [],
    )


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def create_ready_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_chart_ready",
) -> str:
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="Raw Retail Transactions Demo",
        source_type="demo_raw_retail",
        status="ready_for_analysis",
        raw_table_name="RAW_UPLOAD_CHART_TEST",
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
    return dataset.id


def candidates() -> list[ProviderCandidate]:
    return [ProviderCandidate("openai_fallback", "openai", "key", "model")]


def plan_payload(
    *,
    source_model: str = "mart_sales_performance",
    metric: str = "revenue",
    dimensions: list[str] | None = None,
    question: str = "How is revenue performing?",
) -> str:
    dimensions = ["order_month"] if dimensions is None else dimensions
    sort = [{"field": dimensions[0], "direction": "asc"}] if dimensions else []
    return json.dumps(
        {
            "decision_type": "create_new",
            "question": question,
            "intent": "revenue_trend",
            "source_model": source_model,
            "grain": "one row per selected grain",
            "metrics": [{"name": metric, "aggregation": "sum"}],
            "dimensions": dimensions,
            "filters": [],
            "sort": sort,
            "limit": 100,
            "assumptions": [],
            "warnings": [],
        }
    )


def query_result(
    output_schema: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> snowflake_service.SnowflakeQueryResult:
    return snowflake_service.SnowflakeQueryResult(
        output_schema=output_schema,
        preview_rows=rows,
        row_count=len(rows),
    )


def patch_analysis(
    monkeypatch,
    *,
    provider_payload: str,
    snowflake_result: snowflake_service.SnowflakeQueryResult,
) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: candidates(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: provider_payload,
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.snowflake_service.execute_analysis_query",
        lambda **_kwargs: snowflake_result,
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: [],
    )


def post_analysis(
    client: TestClient,
    session_id: str,
    dataset_id: str,
    question: str = "How is revenue performing?",
):
    return client.post(
        "/api/v1/analysis-runs",
        headers={DEMO_SESSION_HEADER: session_id},
        json={
            "attached_dataset_id": dataset_id,
            "question": question,
        },
    )


def test_successful_analysis_creates_chart_from_real_preview_rows(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    rows = [
        {"ORDER_MONTH": "2026-01", "REVENUE": "100.50"},
        {"ORDER_MONTH": "2026-02", "REVENUE": "150.25"},
    ]
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(),
        snowflake_result=query_result(
            [{"name": "ORDER_MONTH", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            rows,
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["chart_generation_status"] == "completed"
    assert len(body["charts"]) == 1
    assert body["charts"][0]["chart_type"] == "line"
    assert body["charts"][0]["data"] == rows
    db_session.expire_all()
    assert len(db_session.scalars(select(AnalysisRunChart)).all()) == 1


def test_kpi_chart_generated_for_single_numeric_aggregate(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(dimensions=[]),
        snowflake_result=query_result(
            [{"name": "REVENUE", "type": "FIXED"}],
            [{"REVENUE": "2500.00"}],
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    chart = response.json()["charts"][0]
    assert chart["chart_type"] == "kpi"
    assert chart["chart_spec"]["value"]["field"] == "REVENUE"


def test_bar_chart_generated_for_category_and_numeric_metric(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(
            source_model="mart_product_performance",
            dimensions=["product_category"],
        ),
        snowflake_result=query_result(
            [{"name": "PRODUCT_CATEGORY", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            [{"PRODUCT_CATEGORY": "Coffee", "REVENUE": "300.00"}],
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    chart = response.json()["charts"][0]
    assert chart["chart_type"] == "bar"
    assert chart["chart_spec"]["x"]["field"] == "PRODUCT_CATEGORY"


def test_horizontal_bar_generated_for_top_ranking_question(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    question = "What are the top product categories by revenue?"
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(
            source_model="mart_product_performance",
            dimensions=["product_category"],
            question=question,
        ),
        snowflake_result=query_result(
            [{"name": "PRODUCT_CATEGORY", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            [{"PRODUCT_CATEGORY": "Coffee", "REVENUE": "300.00"}],
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id, question=question)

    assert response.status_code == 200
    assert response.json()["charts"][0]["chart_type"] == "horizontal_bar"


def test_table_chart_generated_when_shape_is_uncertain(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(),
        snowflake_result=query_result(
            [{"name": "CATEGORY", "type": "TEXT"}, {"name": "VALUE", "type": "TEXT"}],
            [{"CATEGORY": "A", "VALUE": "not numeric"}],
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    chart = response.json()["charts"][0]
    assert chart["chart_type"] == "table"
    assert chart["chart_spec"]["columns"][0]["field"] == "CATEGORY"


def test_chartspec_validation_rejects_unknown_fields_and_types() -> None:
    with pytest.raises(ChartSpecError):
        validate_chart_spec(
            {
                "type": "bar",
                "title": "Bad",
                "x": {"field": "UNKNOWN"},
                "y": {"field": "REVENUE"},
                "source_model": "mart_sales_performance",
            },
            output_schema=[{"name": "ORDER_MONTH", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            rows=[{"ORDER_MONTH": "2026-01", "REVENUE": "100"}],
            source_model="mart_sales_performance",
        )
    with pytest.raises(ChartSpecError):
        validate_chart_spec(
            {"type": "pie", "title": "Nope", "source_model": "mart_sales_performance"},
            output_schema=[{"name": "REVENUE", "type": "FIXED"}],
            rows=[{"REVENUE": "100"}],
            source_model="mart_sales_performance",
        )


def test_chart_count_never_exceeds_three(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(),
        snowflake_result=query_result(
            [{"name": "ORDER_MONTH", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            [{"ORDER_MONTH": "2026-01", "REVENUE": "100"}],
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    assert 0 < len(response.json()["charts"]) <= 3


def test_reused_analysis_returns_existing_charts_without_usage_increment(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(),
        snowflake_result=query_result(
            [{"name": "ORDER_MONTH", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            [{"ORDER_MONTH": "2026-01", "REVENUE": "100"}],
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)
    first_response = post_analysis(client, session_id, dataset_id)
    first_chart_id = first_response.json()["charts"][0]["id"]

    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("provider should not be called for reused analysis")
        ),
    )
    second_response = post_analysis(client, session_id, dataset_id)

    assert second_response.status_code == 200
    assert second_response.json()["reused"] is True
    assert second_response.json()["charts"][0]["id"] == first_chart_id
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).successful_analysis_runs_used == 1


def test_chart_generation_failure_does_not_create_fake_chart_data(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(),
        snowflake_result=query_result(
            [{"name": "ORDER_MONTH", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            [{"ORDER_MONTH": "2026-01", "REVENUE": "100"}],
        ),
    )
    monkeypatch.setattr(
        "app.services.chartspec_service.build_chart_for_analysis",
        lambda analysis_run: (_ for _ in ()).throw(ChartSpecError("shape failed")),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_run"]["status"] == "completed"
    assert body["chart_generation_status"] == "failed"
    assert body["charts"] == []
    db_session.expire_all()
    assert db_session.scalars(select(AnalysisRunChart)).all() == []
    assert db_session.scalar(select(AnalysisRun)).status == "completed"


def test_get_detail_returns_charts_and_blocks_cross_session_access(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis(
        monkeypatch,
        provider_payload=plan_payload(),
        snowflake_result=query_result(
            [{"name": "ORDER_MONTH", "type": "TEXT"}, {"name": "REVENUE", "type": "FIXED"}],
            [{"ORDER_MONTH": "2026-01", "REVENUE": "100"}],
        ),
    )
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, owner_session_id)
    analysis_id = post_analysis(client, owner_session_id, dataset_id).json()["analysis_run"]["id"]

    detail_response = client.get(
        f"/api/v1/analysis-runs/{analysis_id}",
        headers={DEMO_SESSION_HEADER: owner_session_id},
    )
    cross_response = client.get(
        f"/api/v1/analysis-runs/{analysis_id}",
        headers={DEMO_SESSION_HEADER: other_session_id},
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["charts"][0]["analysis_run_id"] == analysis_id
    assert cross_response.status_code == 404
    assert cross_response.json()["error_code"] == "ANALYSIS_RUN_NOT_FOUND"
