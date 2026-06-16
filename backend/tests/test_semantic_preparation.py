import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import (
    AiProviderRun,
    ColumnProfile,
    Dataset,
    DatasetFile,
    DatasetQuestionSuggestion,
    SemanticColumn,
)
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.semantic_preparation_service import ProviderCallError, ProviderCandidate


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def create_profiled_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_semantic_test",
    with_profiles: bool = True,
) -> str:
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="semantic_sales.csv",
        source_type="uploaded_csv",
        status="schema_review",
        raw_table_name="RAW_UPLOAD_SEMANTIC_TEST",
        storage_uri="s3://bucket/key",
        storage_key="key",
        row_count=2,
        column_count=3 if with_profiles else 0,
    )
    db_session.add(dataset)
    if with_profiles:
        dataset_file = DatasetFile(
            dataset=dataset,
            file_name="semantic_sales.csv",
            storage_key="key",
            file_size_bytes=64,
            content_type="text/csv",
            row_count=2,
            column_count=3,
        )
        db_session.add(dataset_file)
        db_session.add_all(
            [
                ColumnProfile(
                    dataset=dataset,
                    dataset_file=dataset_file,
                    column_index=0,
                    raw_column_name="order_id",
                    normalized_column_name="ORDER_ID",
                    snowflake_column_name="ORDER_ID",
                    detected_type="identifier",
                    null_count=0,
                    null_rate=0,
                    unique_count=2,
                    sample_values_json=["1001", "1002"],
                ),
                ColumnProfile(
                    dataset=dataset,
                    dataset_file=dataset_file,
                    column_index=1,
                    raw_column_name="revenue",
                    normalized_column_name="REVENUE",
                    snowflake_column_name="REVENUE",
                    detected_type="decimal",
                    null_count=0,
                    null_rate=0,
                    unique_count=2,
                    sample_values_json=["10.50", "12.75"],
                ),
                ColumnProfile(
                    dataset=dataset,
                    dataset_file=dataset_file,
                    column_index=2,
                    raw_column_name="order_date",
                    normalized_column_name="ORDER_DATE",
                    snowflake_column_name="ORDER_DATE",
                    detected_type="date",
                    null_count=0,
                    null_rate=0,
                    unique_count=2,
                    sample_values_json=["2026-01-01", "2026-01-02"],
                ),
            ]
        )
    db_session.commit()
    return dataset.id


def semantic_payload(
    *,
    revenue_name: str = "revenue",
    question: str = "How is revenue trending over time?",
) -> str:
    return json.dumps(
        {
            "columns": [
                {
                    "raw_column_name": "order_id",
                    "suggested_name": "order_id",
                    "semantic_role": "identifier",
                    "confidence": 0.96,
                    "needs_review": False,
                    "reason": "Order identifier used to count transactions.",
                },
                {
                    "raw_column_name": "revenue",
                    "suggested_name": revenue_name,
                    "semantic_role": "measure_column",
                    "confidence": 0.94,
                    "needs_review": False,
                    "reason": "Numeric monetary amount suitable as a measure.",
                },
                {
                    "raw_column_name": "order_date",
                    "suggested_name": "order_date",
                    "semantic_role": "date_time",
                    "confidence": 0.93,
                    "needs_review": False,
                    "reason": "Date field that can anchor time analysis.",
                },
            ],
            "suggested_questions": [
                {
                    "question": question,
                    "intent": "revenue_trend",
                }
            ],
            "warnings": [],
        }
    )


def configured_candidates() -> list[ProviderCandidate]:
    return [
        ProviderCandidate("gemini_lane_1", "gemini", "key-1", "gemini-model-1"),
        ProviderCandidate("gemini_lane_2", "gemini", "key-2", "gemini-model-2"),
        ProviderCandidate("gemini_lane_3", "gemini", "key-3", "gemini-model-3"),
        ProviderCandidate("openai_fallback", "openai", "openai-key", "openai-model"),
    ]


def post_semantic(client: TestClient, session_id: str | None, dataset_id: str, body=None):
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.post(
        f"/api/v1/datasets/{dataset_id}/semantic-preparation",
        headers=headers,
        json=body,
    )


def test_semantic_prep_requires_session_header(client: TestClient) -> None:
    response = post_semantic(client, None, "ds_missing")

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_semantic_prep_rejects_invalid_session(client: TestClient) -> None:
    response = post_semantic(client, "mf_demo_missing", "ds_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_semantic_prep_rejects_dataset_from_other_session(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, owner_session_id)

    response = post_semantic(client, other_session_id, dataset_id)

    assert response.status_code == 404
    assert response.json()["error_code"] == "DATASET_NOT_FOUND"


def test_semantic_prep_dataset_without_profiles_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id, with_profiles=False)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "DATASET_NOT_READY_FOR_SEMANTIC_PREP"


def test_semantic_prep_no_providers_configured_returns_honest_failed_status(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: [
            ProviderCandidate("gemini_lane_1", "gemini", None, None),
            ProviderCandidate("gemini_lane_2", "gemini", None, None),
            ProviderCandidate("gemini_lane_3", "gemini", None, None),
            ProviderCandidate("openai_fallback", "openai", None, None),
        ],
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["semantic_columns"] == []
    assert body["suggested_questions"] == []
    assert {run["error_code"] for run in body["provider_runs"]} == {
        "AI_PROVIDER_NOT_CONFIGURED"
    }
    db_session.expire_all()
    assert db_session.scalars(select(SemanticColumn)).all() == []
    assert db_session.scalars(select(DatasetQuestionSuggestion)).all() == []


def test_semantic_prep_mocked_gemini_success_stores_suggestions(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: semantic_payload(),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["semantic_columns"]) == 3
    revenue_column = next(
        column
        for column in body["semantic_columns"]
        if column["raw_column_name"] == "revenue"
    )
    assert revenue_column["semantic_role"] == "measure_column"
    assert revenue_column["provider_name"] == "gemini"
    assert body["suggested_questions"][0]["question"] == "How is revenue trending over time?"

    db_session.expire_all()
    assert len(db_session.scalars(select(SemanticColumn)).all()) == 3
    assert len(db_session.scalars(select(DatasetQuestionSuggestion)).all()) == 1
    runs = db_session.scalars(select(AiProviderRun)).all()
    assert [run.status for run in runs] == ["completed"]


def test_semantic_prep_tries_gemini_lane_two_after_lane_one_failure(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )

    def call_gemini(candidate, prompt, temperature):
        if candidate.lane_name == "gemini_lane_1":
            raise ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "lane 1 failed")
        return semantic_payload(question="Which customer segments drive revenue?")

    monkeypatch.setattr("app.services.semantic_preparation_service.call_gemini_provider", call_gemini)
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert [run["provider_name"] for run in body["provider_runs"]] == [
        "gemini_lane_1",
        "gemini_lane_2",
    ]
    assert body["provider_runs"][1]["fallback_from_provider"] == "gemini_lane_1"
    assert body["suggested_questions"][0]["intent"] == "revenue_trend"


def test_semantic_prep_uses_openai_fallback_after_gemini_failures(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "gemini failed")
        ),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_openai_provider",
        lambda candidate, prompt, temperature: semantic_payload(question="What revenue changed by date?"),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["provider_runs"][-1]["provider_name"] == "openai_fallback"
    assert body["semantic_columns"][0]["provider_name"] == "openai"


def test_invalid_provider_output_triggers_fallback(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )

    def call_gemini(candidate, prompt, temperature):
        if candidate.lane_name == "gemini_lane_1":
            return "not-json"
        return semantic_payload()

    monkeypatch.setattr("app.services.semantic_preparation_service.call_gemini_provider", call_gemini)
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["provider_runs"][0]["error_code"] == "AI_PROVIDER_OUTPUT_INVALID"
    assert body["provider_runs"][1]["status"] == "completed"


def test_all_provider_failures_do_not_store_fake_suggestions(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "gemini failed")
        ),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_openai_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "openai failed")
        ),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)

    response = post_semantic(client, session_id, dataset_id)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    db_session.expire_all()
    assert db_session.scalars(select(SemanticColumn)).all() == []
    assert db_session.scalars(select(DatasetQuestionSuggestion)).all() == []


def test_existing_suggestions_are_reused_when_force_false(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: semantic_payload(),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)
    first_response = post_semantic(client, session_id, dataset_id)
    assert first_response.status_code == 200

    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: (_ for _ in ()).throw(
            AssertionError("provider should not be called")
        ),
    )
    second_response = post_semantic(client, session_id, dataset_id)

    assert second_response.status_code == 200
    assert second_response.json()["status"] == "completed"
    db_session.expire_all()
    assert len(db_session.scalars(select(AiProviderRun)).all()) == 1


def test_force_true_refreshes_existing_suggestions(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    payloads = iter([semantic_payload(), semantic_payload(revenue_name="net_revenue")])
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: next(payloads),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)
    assert post_semantic(client, session_id, dataset_id).status_code == 200

    response = post_semantic(client, session_id, dataset_id, {"force": True})

    assert response.status_code == 200
    revenue_column = next(
        column
        for column in response.json()["semantic_columns"]
        if column["raw_column_name"] == "revenue"
    )
    assert revenue_column["suggested_name"] == "net_revenue"
    db_session.expire_all()
    assert len(db_session.scalars(select(SemanticColumn)).all()) == 3
    assert len(db_session.scalars(select(AiProviderRun)).all()) == 2


def test_patch_mapping_updates_approved_values_and_marks_user_edited(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: semantic_payload(),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)
    response = post_semantic(client, session_id, dataset_id)
    revenue_column = next(
        column
        for column in response.json()["semantic_columns"]
        if column["raw_column_name"] == "revenue"
    )

    patch_response = client.patch(
        f"/api/v1/datasets/{dataset_id}/semantic-columns",
        headers={DEMO_SESSION_HEADER: session_id},
        json={
            "columns": [
                {
                    "column_profile_id": revenue_column["column_profile_id"],
                    "approved_name": "net_revenue",
                    "approved_role": "measure_column",
                    "include_in_model": True,
                }
            ]
        },
    )

    assert patch_response.status_code == 200
    patched = next(
        column
        for column in patch_response.json()["semantic_columns"]
        if column["raw_column_name"] == "revenue"
    )
    assert patched["approved_name"] == "net_revenue"
    assert patched["approved_role"] == "measure_column"
    assert patched["user_edited"] is True


def test_patch_mapping_rejects_invalid_role_or_name(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)
    profile = db_session.scalar(select(ColumnProfile).where(ColumnProfile.raw_column_name == "revenue"))

    response = client.patch(
        f"/api/v1/datasets/{dataset_id}/semantic-columns",
        headers={DEMO_SESSION_HEADER: session_id},
        json={
            "columns": [
                {
                    "column_profile_id": profile.id,
                    "approved_name": "bad name",
                    "approved_role": "not_a_role",
                    "include_in_model": True,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "SEMANTIC_MAPPING_INVALID"


def test_dataset_detail_exposes_semantic_status_and_suggestions(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.provider_candidates",
        lambda _config: configured_candidates(),
    )
    monkeypatch.setattr(
        "app.services.semantic_preparation_service.call_gemini_provider",
        lambda candidate, prompt, temperature: semantic_payload(),
    )
    session_id = create_session(client)
    dataset_id = create_profiled_dataset(db_session, session_id)
    assert post_semantic(client, session_id, dataset_id).status_code == 200

    response = client.get(
        f"/api/v1/datasets/{dataset_id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["semantic_preparation"]["status"] == "completed"
    assert len(body["semantic_preparation"]["semantic_columns"]) == 3
    assert body["semantic_preparation"]["suggested_questions"][0]["intent"] == "revenue_trend"
