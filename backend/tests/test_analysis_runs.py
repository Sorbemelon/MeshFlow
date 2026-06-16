import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import AnalysisRun, Dataset, DatasetTransformationRun
from app.models.demo_session import DemoSession
from app.services import snowflake_service
from app.services.analysis_run_service import (
    AnalysisPlanValidationError,
    RAW_RETAIL_ANALYSIS_CATALOG,
    generate_analysis_sql,
    validate_analysis_plan,
)
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.semantic_preparation_service import ProviderCallError, ProviderCandidate


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


def configured_candidates() -> list[ProviderCandidate]:
    return [
        ProviderCandidate("openai_primary", "openai", "openai-key", "openai-model"),
        ProviderCandidate("gemini_lane_1", "gemini", "key-1", "gemini-model-1"),
        ProviderCandidate("gemini_lane_2", "gemini", "key-2", "gemini-model-2"),
        ProviderCandidate("gemini_lane_3", "gemini", "key-3", "gemini-model-3"),
    ]


def plan_payload(
    *,
    source_model: str = "mart_sales_performance",
    metric: str = "revenue",
    dimension: str = "order_month",
) -> str:
    return json.dumps(
        {
            "decision_type": "create_new",
            "question": "How is revenue performing?",
            "intent": "revenue_trend",
            "source_model": source_model,
            "grain": "one row per month",
            "metrics": [{"name": metric, "aggregation": "sum"}],
            "dimensions": [dimension],
            "filters": [],
            "sort": [{"field": dimension, "direction": "asc"}],
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
        preview_rows=[{"ORDER_MONTH": "2026-01", "REVENUE": "1250.50"}],
        row_count=1,
    )


def create_ready_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_analysis_ready",
    status: str = "ready_for_analysis",
    source_type: str = "demo_raw_retail",
    deleted: bool = False,
) -> str:
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="Raw Retail Transactions Demo",
        source_type=source_type,
        status=status,
        raw_table_name="RAW_UPLOAD_ANALYSIS_TEST",
        storage_uri="s3://bucket/key",
        storage_key="key",
        row_count=4,
        column_count=18,
    )
    if deleted:
        dataset.deleted_at = datetime.now(UTC)
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


def post_analysis(
    client: TestClient,
    session_id: str | None,
    *,
    dataset_id: str | None = "ds_analysis_ready",
    question: str = "How is revenue performing?",
    force_new: bool = False,
):
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    body: dict[str, object] = {"question": question, "force_new": force_new}
    if dataset_id is not None:
        body["attached_dataset_id"] = dataset_id
    return client.post("/api/v1/analysis-runs", headers=headers, json=body)


def patch_successful_analysis(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: plan_payload(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_gemini_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("Gemini should not be called when OpenAI succeeds")
        ),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.snowflake_service.execute_analysis_query",
        lambda **_kwargs: query_result(),
    )
    monkeypatch.setattr(
        "app.services.insight_generation_service.provider_candidates",
        lambda _config: [],
    )


def test_create_analysis_requires_session_header(client: TestClient) -> None:
    response = post_analysis(client, None)

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_create_analysis_rejects_invalid_session(client: TestClient) -> None:
    response = post_analysis(client, "mf_demo_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_create_analysis_requires_attached_dataset_id(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_analysis(client, session_id, dataset_id=None)

    assert response.status_code == 400
    assert response.json()["error_code"] == "ATTACHED_DATASET_REQUIRED"


def test_create_analysis_rejects_dataset_from_other_session(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, owner_session_id)

    response = post_analysis(client, other_session_id, dataset_id=dataset_id)

    assert response.status_code == 404
    assert response.json()["error_code"] == "DATASET_NOT_FOUND"


def test_create_analysis_rejects_dataset_not_ready(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id, status="schema_review")

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "DATASET_NOT_READY_FOR_ANALYSIS"


def test_create_analysis_rejects_deleted_dataset(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id, deleted=True)

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 410
    assert response.json()["error_code"] == "DATASET_DELETED"


def test_provider_unavailable_returns_honest_failure_without_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: [
            ProviderCandidate("openai_primary", "openai", None, None),
            ProviderCandidate("gemini_lane_1", "gemini", None, None),
            ProviderCandidate("gemini_lane_2", "gemini", None, None),
            ProviderCandidate("gemini_lane_3", "gemini", None, None),
        ],
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 502
    assert response.json()["error_code"] == "ANALYSIS_PLAN_FAILED"
    db_session.expire_all()
    run = db_session.scalar(select(AnalysisRun))
    assert run.status == "failed"
    assert run.generated_sql is None
    assert db_session.get(DemoSession, session_id).successful_analysis_runs_used == 0


def test_invalid_provider_output_falls_back_to_gemini(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: "not-json",
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_gemini_provider",
        lambda candidate, prompt, temperature: plan_payload(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.snowflake_service.execute_analysis_query",
        lambda **_kwargs: query_result(),
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 200
    provider_runs = response.json()["analysis_run"]["provider_runs"]
    assert [run["provider_name"] for run in provider_runs] == [
        "openai_primary",
        "gemini_lane_1",
    ]
    assert provider_runs[0]["error_code"] == "ANALYSIS_PLAN_INVALID"
    assert provider_runs[1]["status"] == "completed"


def test_openai_success_generates_query_and_skips_gemini(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_successful_analysis(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 200
    body = response.json()
    analysis_run = body["analysis_run"]
    assert analysis_run["status"] == "completed"
    assert analysis_run["provider_runs"][0]["provider_name"] == "openai_primary"
    assert analysis_run["generated_sql"].startswith("SELECT")
    assert "MART_SALES_PERFORMANCE" in analysis_run["generated_sql"]
    assert analysis_run["preview_rows"] == [{"ORDER_MONTH": "2026-01", "REVENUE": "1250.50"}]


def test_all_providers_invalid_do_not_store_fake_success(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: "not-json",
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_gemini_provider",
        lambda candidate, prompt, temperature: "not-json",
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 502
    db_session.expire_all()
    run = db_session.scalar(select(AnalysisRun))
    assert run.status == "failed"
    assert run.preview_rows_json is None
    assert db_session.get(DemoSession, session_id).successful_analysis_runs_used == 0


def test_plan_validation_rejects_unknown_catalog_parts() -> None:
    with pytest.raises(AnalysisPlanValidationError):
        validate_analysis_plan(
            plan_payload(source_model="mart_fake"),
            RAW_RETAIL_ANALYSIS_CATALOG,
        )
    with pytest.raises(AnalysisPlanValidationError):
        validate_analysis_plan(
            plan_payload(metric="fake_metric"),
            RAW_RETAIL_ANALYSIS_CATALOG,
        )
    with pytest.raises(AnalysisPlanValidationError):
        validate_analysis_plan(
            plan_payload(dimension="fake_dimension"),
            RAW_RETAIL_ANALYSIS_CATALOG,
        )


def test_valid_plan_generates_backend_owned_select_only_sql() -> None:
    plan = validate_analysis_plan(plan_payload(), RAW_RETAIL_ANALYSIS_CATALOG)

    sql = generate_analysis_sql(plan)

    assert sql.startswith("SELECT")
    assert "FROM" in sql
    assert "MART_SALES_PERFORMANCE" in sql
    assert "GROUP BY" in sql
    assert "LIMIT 100" in sql
    assert "DROP" not in sql
    assert ";" not in sql


def test_snowflake_query_failure_marks_failed_without_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.analysis_run_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: plan_payload(),
    )

    def fail_query(**_kwargs):
        raise snowflake_service.SnowflakeServiceError("query failed")

    monkeypatch.setattr(
        "app.services.analysis_run_service.snowflake_service.execute_analysis_query",
        fail_query,
    )
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 502
    assert response.json()["error_code"] == "ANALYSIS_QUERY_FAILED"
    db_session.expire_all()
    run = db_session.scalar(select(AnalysisRun))
    assert run.status == "failed"
    assert run.failed_step == "snowflake_analysis_query"
    assert db_session.get(DemoSession, session_id).successful_analysis_runs_used == 0


def test_successful_analysis_increments_usage_and_workspace_history(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_successful_analysis(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)

    response = post_analysis(client, session_id, dataset_id=dataset_id)
    workspace_response = client.get(
        "/api/v1/workspace",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).successful_analysis_runs_used == 1
    workspace = workspace_response.json()
    assert workspace["history"]["successful_analysis_runs_used"] == 1
    assert workspace["history"]["analysis_runs"][0]["status"] == "completed"


def test_reusing_same_completed_question_does_not_increment_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_successful_analysis(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)
    first_response = post_analysis(client, session_id, dataset_id=dataset_id)
    first_id = first_response.json()["analysis_run"]["id"]

    monkeypatch.setattr(
        "app.services.analysis_run_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("provider should not be called for reuse")
        ),
    )
    second_response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert second_response.status_code == 200
    body = second_response.json()
    assert body["reused"] is True
    assert body["analysis_run"]["id"] == first_id
    assert body["analysis_run"]["decision_type"] == "reuse_existing"
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).successful_analysis_runs_used == 1


def test_analysis_quota_blocks_new_runs_at_limit(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_successful_analysis(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, session_id)
    session = db_session.get(DemoSession, session_id)
    session.successful_analysis_runs_used = 8
    db_session.commit()

    response = post_analysis(client, session_id, dataset_id=dataset_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "ANALYSIS_LIMIT_REACHED"


def test_analysis_list_and_detail_are_session_scoped(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_successful_analysis(monkeypatch)
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset_id = create_ready_dataset(db_session, owner_session_id)
    other_dataset_id = create_ready_dataset(
        db_session,
        other_session_id,
        dataset_id="ds_analysis_other",
    )
    first_response = post_analysis(client, owner_session_id, dataset_id=dataset_id)
    other_response = post_analysis(
        client,
        other_session_id,
        dataset_id=other_dataset_id,
        question="How are store orders performing?",
        force_new=True,
    )
    analysis_run_id = first_response.json()["analysis_run"]["id"]
    other_analysis_id = other_response.json()["analysis_run"]["id"]

    list_response = client.get(
        "/api/v1/analysis-runs",
        headers={DEMO_SESSION_HEADER: owner_session_id},
    )
    detail_response = client.get(
        f"/api/v1/analysis-runs/{analysis_run_id}",
        headers={DEMO_SESSION_HEADER: owner_session_id},
    )
    cross_detail_response = client.get(
        f"/api/v1/analysis-runs/{other_analysis_id}",
        headers={DEMO_SESSION_HEADER: owner_session_id},
    )

    assert list_response.status_code == 200
    assert [run["id"] for run in list_response.json()["analysis_runs"]] == [analysis_run_id]
    assert detail_response.status_code == 200
    assert detail_response.json()["analysis_run"]["id"] == analysis_run_id
    assert cross_detail_response.status_code == 404
    assert cross_detail_response.json()["error_code"] == "ANALYSIS_RUN_NOT_FOUND"
