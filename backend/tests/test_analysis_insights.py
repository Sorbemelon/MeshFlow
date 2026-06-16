import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import (
    AiProviderRun,
    AnalysisInsight,
    AnalysisRun,
    Dataset,
    DatasetTransformationRun,
)
from app.services import snowflake_service
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.semantic_preparation_service import ProviderCallError, ProviderCandidate


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def create_ready_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_insight_ready",
) -> str:
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="Raw Retail Transactions Demo",
        source_type="demo_raw_retail",
        status="ready_for_analysis",
        raw_table_name="RAW_UPLOAD_INSIGHT_TEST",
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


def analysis_candidates() -> list[ProviderCandidate]:
    return [ProviderCandidate("openai_primary", "openai", "openai-key", "openai-model")]


def insight_candidates() -> list[ProviderCandidate]:
    return [
        ProviderCandidate("gemini_lane_1", "gemini", "key-1", "gemini-model-1"),
        ProviderCandidate("gemini_lane_2", "gemini", "key-2", "gemini-model-2"),
        ProviderCandidate("gemini_lane_3", "gemini", "key-3", "gemini-model-3"),
        ProviderCandidate("openai_fallback", "openai", "openai-key", "openai-model"),
    ]


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


def insight_payload(*, chart_title: str = "Revenue Trend") -> str:
    return json.dumps(
        {
            "question_insight": {
                "summary": "Revenue is higher in February than January in the preview.",
                "key_findings": [
                    "February revenue is 150.25 while January revenue is 100.50."
                ],
                "tags": ["trend", "revenue"],
                "confidence": "medium",
            },
            "chart_insights": [
                {
                    "chart_title": chart_title,
                    "summary": "The chart rises from January to February.",
                    "key_findings": ["The previewed line has two monthly points."],
                    "tags": ["trend"],
                    "confidence": "medium",
                }
            ],
            "warnings": [],
        }
    )


def query_result() -> snowflake_service.SnowflakeQueryResult:
    return snowflake_service.SnowflakeQueryResult(
        output_schema=[
            {"name": "ORDER_MONTH", "type": "TEXT"},
            {"name": "REVENUE", "type": "FIXED"},
        ],
        preview_rows=[
            {"ORDER_MONTH": "2026-01", "REVENUE": "100.50"},
            {"ORDER_MONTH": "2026-02", "REVENUE": "150.25"},
        ],
        row_count=2,
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


def patch_insight_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: insight_candidates(),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: insight_payload(),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("OpenAI should not be called when Gemini succeeds")
        ),
    )


def post_analysis(client: TestClient, session_id: str, dataset_id: str):
    return client.post(
        "/api/v1/analysis-runs",
        headers={DEMO_SESSION_HEADER: session_id},
        json={
            "attached_dataset_id": dataset_id,
            "question": "How is revenue performing?",
        },
    )


def test_successful_analysis_stores_question_and_chart_insights(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    patch_insight_success(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["insight_generation_status"] == "completed"
    assert {insight["insight_level"] for insight in body["insights"]} == {"question", "chart"}
    assert body["insights"][0]["summary"]
    db_session.expire_all()
    insights = db_session.scalars(select(AnalysisInsight)).all()
    assert len(insights) == 2
    assert {insight.status for insight in insights} == {"completed"}


def test_gemini_lane_one_success_skips_fallback(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    patch_insight_success(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    provider_runs = [
        run
        for run in db_session.scalars(select(AiProviderRun)).all()
        if run.task_type == "insight_generation"
    ]
    assert [run.provider_name for run in provider_runs] == ["gemini_lane_1"]
    assert provider_runs[0].status == "completed"


def test_gemini_lane_failure_uses_next_gemini_lane(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: insight_candidates(),
    )

    def gemini(candidate, prompt, temperature):
        if candidate.lane_name == "gemini_lane_1":
            raise ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "lane one failed")
        return insight_payload()

    monkeypatch.setattr("app.services.insight_generation_service.call_gemini_provider", gemini)
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("OpenAI should not be needed")
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    provider_runs = [
        run
        for run in db_session.scalars(select(AiProviderRun)).all()
        if run.task_type == "insight_generation"
    ]
    assert [run.provider_name for run in provider_runs] == ["gemini_lane_1", "gemini_lane_2"]
    assert provider_runs[0].status == "failed"
    assert provider_runs[1].status == "completed"


def test_openai_fallback_succeeds_after_gemini_failures(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: insight_candidates(),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "gemini failed")
        ),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_openai_provider",
        lambda candidate, prompt, temperature: insight_payload(),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    insight_runs = [
        run
        for run in db_session.scalars(select(AiProviderRun)).all()
        if run.task_type == "insight_generation"
    ]
    assert insight_runs[-1].provider_name == "openai_fallback"
    assert insight_runs[-1].status == "completed"


def test_invalid_insight_output_triggers_fallback(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: insight_candidates(),
    )

    def gemini(candidate, prompt, temperature):
        if candidate.lane_name == "gemini_lane_1":
            return "not-json"
        return insight_payload()

    monkeypatch.setattr("app.services.insight_generation_service.call_gemini_provider", gemini)
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("OpenAI should not be needed")
        ),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    insight_runs = [
        run
        for run in db_session.scalars(select(AiProviderRun)).all()
        if run.task_type == "insight_generation"
    ]
    assert insight_runs[0].error_code == "INSIGHT_PROVIDER_OUTPUT_INVALID"
    assert insight_runs[1].status == "completed"


def test_all_insight_providers_fail_preserves_completed_analysis_and_charts(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: insight_candidates(),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: "not-json",
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.call_openai_provider",
        lambda candidate, prompt, temperature: "not-json",
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_run"]["status"] == "completed"
    assert body["charts"]
    assert body["insight_generation_status"] == "failed"
    db_session.expire_all()
    run = db_session.scalar(select(AnalysisRun))
    assert run.status == "completed"
    completed_insights = db_session.scalars(
        select(AnalysisInsight).where(AnalysisInsight.status == "completed")
    ).all()
    assert completed_insights == []


def test_reused_analysis_returns_existing_insights_without_provider_call(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    patch_insight_success(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)
    first_response = post_analysis(client, session_id, dataset_id)

    monkeypatch.setattr(
        "app.services.insight_generation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("Insight provider should not be called for existing insights")
        ),
    )
    second_response = post_analysis(client, session_id, dataset_id)

    assert second_response.status_code == 200
    assert second_response.json()["reused"] is True
    assert {insight["id"] for insight in second_response.json()["insights"]} == {
        insight["id"] for insight in first_response.json()["insights"]
    }
    db_session.expire_all()
    assert len(db_session.scalars(select(AnalysisInsight)).all()) == 2


def test_detail_and_list_return_real_insight_evidence(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    patch_insight_success(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)
    analysis_id = post_analysis(client, session_id, dataset_id).json()["analysis_run"]["id"]

    detail = client.get(
        f"/api/v1/analysis-runs/{analysis_id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    listing = client.get(
        "/api/v1/analysis-runs",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["analysis_run"]["generated_sql"].startswith("SELECT")
    assert detail_body["analysis_run"]["output_schema"]
    assert detail_body["analysis_run"]["preview_rows"]
    assert detail_body["charts"][0]["chart_spec"]
    assert detail_body["insights"]
    assert any(
        run["task_type"] == "insight_generation"
        for run in detail_body["analysis_run"]["provider_runs"]
    )
    assert listing.status_code == 200
    summary = listing.json()["analysis_runs"][0]
    assert summary["dataset_name"] == "Raw Retail Transactions Demo"
    assert summary["chart_count"] == 1
    assert summary["insight_status"] == "completed"


def test_cross_session_detail_access_is_blocked(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_analysis_success(monkeypatch)
    patch_insight_success(monkeypatch)
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, owner_session_id)
    analysis_id = post_analysis(client, owner_session_id, dataset_id).json()["analysis_run"]["id"]

    response = client.get(
        f"/api/v1/analysis-runs/{analysis_id}",
        headers={DEMO_SESSION_HEADER: other_session_id},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "ANALYSIS_RUN_NOT_FOUND"
