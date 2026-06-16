from subprocess import CompletedProcess

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import dbt_transformation_service
from app.models.dataset import (
    ColumnProfile,
    DataFlowEdge,
    DataFlowNode,
    Dataset,
    DatasetFile,
    DatasetTransformationRun,
    DbtArtifact,
    SemanticColumn,
)
from app.models.demo_session import DemoSession
from app.schemas.upload_preflight import ReadinessCheck
from app.services.dbt_transformation_service import DbtExecutionError
from app.services.demo_session_service import DEMO_SESSION_HEADER


RAW_RETAIL_COLUMNS = [
    "order_id",
    "order_line_id",
    "order_date",
    "customer_id",
    "customer_name",
    "customer_segment",
    "product_id",
    "product_name",
    "product_category",
    "store_id",
    "store_name",
    "store_region",
    "quantity",
    "unit_price",
    "discount_amount",
    "revenue",
    "cost",
    "payment_method",
]


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def ready_check() -> ReadinessCheck:
    return ReadinessCheck(status="ready", message="Ready.", next_action=None)


def post_transform(client: TestClient, session_id: str | None, dataset_id: str, body=None):
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.post(
        f"/api/v1/datasets/{dataset_id}/transform",
        headers=headers,
        json=body,
    )


def create_dataset(
    db_session: Session,
    session_id: str,
    *,
    dataset_id: str = "ds_transform_test",
    source_type: str = "demo_raw_retail",
    with_profiles: bool = True,
    with_semantic: bool = True,
    raw_table_name: str = "RAW_UPLOAD_TRANSFORM_TEST",
) -> str:
    columns = RAW_RETAIL_COLUMNS if source_type == "demo_raw_retail" else [
        "order_id",
        "revenue",
        "order_date",
    ]
    dataset = Dataset(
        id=dataset_id,
        demo_session_id=session_id,
        name="Raw Retail Transactions Demo" if source_type == "demo_raw_retail" else "sales.csv",
        source_type=source_type,
        status="schema_review",
        raw_table_name=raw_table_name,
        storage_uri="s3://bucket/key",
        storage_key="key",
        row_count=4,
        column_count=len(columns) if with_profiles else 0,
    )
    db_session.add(dataset)
    if with_profiles:
        dataset_file = DatasetFile(
            dataset=dataset,
            file_name="raw_retail_transactions_demo.csv",
            storage_key="key",
            file_size_bytes=128,
            content_type="text/csv",
            row_count=4,
            column_count=len(columns),
        )
        db_session.add(dataset_file)
        profiles: list[ColumnProfile] = []
        for index, column_name in enumerate(columns):
            snowflake_name = column_name.upper()
            detected_type = "decimal" if column_name in {"revenue", "cost", "unit_price"} else "string"
            if column_name.endswith("_id"):
                detected_type = "identifier"
            if column_name == "order_date":
                detected_type = "date"
            profile = ColumnProfile(
                dataset=dataset,
                dataset_file=dataset_file,
                column_index=index,
                raw_column_name=column_name,
                normalized_column_name=snowflake_name,
                snowflake_column_name=snowflake_name,
                detected_type=detected_type,
                null_count=0,
                null_rate=0,
                unique_count=4,
                sample_values_json=["sample"],
            )
            db_session.add(profile)
            profiles.append(profile)

        if with_semantic:
            for profile in profiles:
                role = "dimension"
                if profile.raw_column_name.endswith("_id"):
                    role = "identifier"
                if profile.raw_column_name == "order_date":
                    role = "date_time"
                if profile.raw_column_name in {"revenue", "cost", "unit_price", "quantity"}:
                    role = "measure_column"
                db_session.add(
                    SemanticColumn(
                        dataset=dataset,
                        column_profile=profile,
                        raw_column_name=profile.raw_column_name,
                        suggested_name=profile.raw_column_name,
                        semantic_role=role,
                        confidence=0.95,
                        needs_review=False,
                        reason="Test mapping.",
                        approved_name=profile.raw_column_name,
                        approved_role=role,
                    )
                )

    db_session.commit()
    return dataset.id


def patch_transform_dependencies(monkeypatch, *, fail: bool = False) -> None:
    monkeypatch.setattr(
        "app.services.dbt_transformation_service.readiness_service.check_snowflake_readiness",
        lambda _config: ready_check(),
    )

    def run_dbt(**_kwargs):
        if fail:
            raise DbtExecutionError(
                error_code="DBT_RUN_FAILED",
                failed_step="data_marts",
                message="dbt could not build the Data Marts for this dataset.",
                command_summary={"stdout_tail": "failed"},
            )
        return {
            "debug": {"returncode": 0, "stdout_tail": "debug ok"},
            "run": {"returncode": 0, "stdout_tail": "run ok"},
        }

    monkeypatch.setattr("app.services.dbt_transformation_service.run_dbt_commands", run_dbt)


def test_run_dbt_commands_uses_resolved_project_and_profiles_paths(
    monkeypatch,
    tmp_path,
) -> None:
    project_dir = tmp_path / "dbt_project"
    profiles_dir = project_dir / "profiles"
    profiles_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dbt_transformation_service, "_dbt_executable", lambda: "dbt")
    calls = []

    def fake_run(args, cwd, **_kwargs):
        calls.append((args, cwd))
        return CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(dbt_transformation_service.subprocess, "run", fake_run)

    dbt_transformation_service.run_dbt_commands(
        project_dir=project_dir.relative_to(tmp_path),
        profiles_dir=profiles_dir.relative_to(tmp_path),
        target_name="dev",
    )

    assert calls
    for args, cwd in calls:
        assert cwd == project_dir.resolve()
        assert args[args.index("--project-dir") + 1] == str(project_dir.resolve())
        assert args[args.index("--profiles-dir") + 1] == str(profiles_dir.resolve())


def test_raw_retail_fact_sales_exposes_order_month_for_sales_mart() -> None:
    sql_files = dbt_transformation_service._retail_sql('"RAW_UPLOAD_TEST"')

    assert "date_trunc('month', order_date)::date as order_month" in sql_files[
        "models/dimensional/fact_sales.sql"
    ]


def test_transform_requires_session_header(client: TestClient) -> None:
    response = post_transform(client, None, "ds_missing")

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_transform_rejects_invalid_session(client: TestClient) -> None:
    response = post_transform(client, "mf_demo_missing", "ds_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_transform_rejects_dataset_from_other_session(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_session_id = create_session(client)
    other_session_id = create_session(client)
    dataset_id = create_dataset(db_session, owner_session_id)

    response = post_transform(client, other_session_id, dataset_id)

    assert response.status_code == 404
    assert response.json()["error_code"] == "DATASET_NOT_FOUND"


def test_transform_dataset_without_warehouse_raw_or_profile_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    no_raw_dataset_id = create_dataset(
        db_session,
        session_id,
        dataset_id="ds_no_raw",
        raw_table_name="",
    )
    no_profile_dataset_id = create_dataset(
        db_session,
        session_id,
        dataset_id="ds_no_profile",
        with_profiles=False,
    )

    no_raw_response = post_transform(client, session_id, no_raw_dataset_id)
    no_profile_response = post_transform(client, session_id, no_profile_dataset_id)

    assert no_raw_response.status_code == 400
    assert no_raw_response.json()["error_code"] == "DATASET_NOT_READY_FOR_TRANSFORM"
    assert no_profile_response.status_code == 400
    assert no_profile_response.json()["error_code"] == "DATASET_NOT_READY_FOR_TRANSFORM"


def test_transform_without_semantic_mappings_fails(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id, with_semantic=False)

    response = post_transform(client, session_id, dataset_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "SEMANTIC_MAPPING_REQUIRED"


def test_raw_retail_transform_success_creates_evidence_and_ready_dataset(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_transform_dependencies(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id)
    session_before = db_session.get(DemoSession, session_id)

    response = post_transform(client, session_id, dataset_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["dataset"]["status"] == "ready_for_analysis"
    assert body["layers_completed"] == [
        "staging",
        "intermediate",
        "dimensional_model",
        "data_marts",
    ]
    assert body["models"]["staging"] == ["stg_retail_transactions"]
    assert "mart_sales_performance" in body["models"]["data_marts"]
    assert body["next_route"] == "/demo/dashboard"

    db_session.expire_all()
    dataset = db_session.get(Dataset, dataset_id)
    assert dataset.status == "ready_for_analysis"
    assert len(db_session.scalars(select(DatasetTransformationRun)).all()) == 1
    assert len(db_session.scalars(select(DbtArtifact)).all()) >= 10
    assert len(db_session.scalars(select(DataFlowNode)).all()) == 6
    assert len(db_session.scalars(select(DataFlowEdge)).all()) == 5
    session_after = db_session.get(DemoSession, session_id)
    assert session_after.successful_analysis_runs_used == session_before.successful_analysis_runs_used
    assert session_after.dashboard_cards_used == session_before.dashboard_cards_used

    workspace_response = client.get(
        "/api/v1/workspace",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    workspace = workspace_response.json()
    assert [dataset["id"] for dataset in workspace["ready_datasets"]] == [dataset_id]


def test_raw_retail_transform_failure_stores_failed_run_without_ready(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_transform_dependencies(monkeypatch, fail=True)
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id)

    response = post_transform(client, session_id, dataset_id)

    assert response.status_code == 502
    assert response.json()["error_code"] == "DBT_RUN_FAILED"
    db_session.expire_all()
    dataset = db_session.get(Dataset, dataset_id)
    assert dataset.status == "transform_failed"
    run = db_session.scalar(select(DatasetTransformationRun))
    assert run.status == "failed"
    assert run.failed_step == "data_marts"


def test_uploaded_csv_with_insufficient_mappings_returns_needs_review(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id, source_type="uploaded_csv")
    revenue_mapping = db_session.scalar(
        select(SemanticColumn).where(SemanticColumn.raw_column_name == "revenue")
    )
    revenue_mapping.include_in_model = False
    db_session.commit()

    response = post_transform(client, session_id, dataset_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "TRANSFORMATION_NEEDS_REVIEW"


def test_transform_retry_after_failure_can_succeed(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_transform_dependencies(monkeypatch, fail=True)
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id)
    assert post_transform(client, session_id, dataset_id).status_code == 502

    patch_transform_dependencies(monkeypatch, fail=False)
    retry_response = post_transform(client, session_id, dataset_id)

    assert retry_response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Dataset, dataset_id).status == "ready_for_analysis"
    assert len(db_session.scalars(select(DatasetTransformationRun)).all()) == 2


def test_dbt_artifact_storage_does_not_persist_secrets(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_transform_dependencies(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id)

    response = post_transform(client, session_id, dataset_id)

    assert response.status_code == 200
    db_session.expire_all()
    artifact_text = "\n".join(
        artifact.content_redacted for artifact in db_session.scalars(select(DbtArtifact)).all()
    )
    assert "SNOWFLAKE_PASSWORD" in artifact_text
    assert "secret" not in artifact_text.lower()


def test_data_flow_endpoint_returns_transformation_evidence(
    client: TestClient,
    monkeypatch,
    db_session: Session,
) -> None:
    patch_transform_dependencies(monkeypatch)
    session_id = create_session(client)
    dataset_id = create_dataset(db_session, session_id)
    assert post_transform(client, session_id, dataset_id).status_code == 200

    response = client.get(
        f"/api/v1/datasets/{dataset_id}/data-flow",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]["status"] == "ready_for_analysis"
    assert body["transformation"]["status"] == "completed"
    assert [node["status"] for node in body["nodes"]] == ["completed"] * 6
    assert body["models"]["data_marts"]
