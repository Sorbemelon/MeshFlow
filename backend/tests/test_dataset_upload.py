from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import ColumnProfile, Dataset, DatasetFile
from app.models.demo_session import DemoSession
from app.schemas.upload_preflight import ReadinessCheck
from app.services import snowflake_service, storage_service
from app.services.demo_session_service import DEMO_SESSION_HEADER


CSV_CONTENT = b"order_id,revenue,order_date\n1001,10.50,2026-01-01\n1002,,2026-01-02\n"


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def post_upload(
    client: TestClient,
    session_id: str | None,
    content: bytes,
    *,
    file_name: str = "sales.csv",
) -> object:
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": (file_name, content, "text/csv")},
    )


def ready_check() -> ReadinessCheck:
    return ReadinessCheck(status="ready", message="Ready.", next_action=None)


def not_configured_check(name: str) -> ReadinessCheck:
    return ReadinessCheck(
        status="not_configured",
        message=f"{name} is not configured.",
        next_action=f"Set {name} configuration.",
    )


def patch_ready_dependencies(monkeypatch, *, rows_loaded: int = 2) -> None:
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_s3_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_snowflake_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.storage_service.upload_csv_to_s3",
        lambda **_kwargs: storage_service.StorageUploadResult(
            storage_key="meshflow-demo/sessions/session/raw/dataset/sales.csv",
            storage_uri="s3://bucket/meshflow-demo/sessions/session/raw/dataset/sales.csv",
        ),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.snowflake_service.create_and_load_raw_table",
        lambda **_kwargs: snowflake_service.SnowflakeLoadResult(
            raw_table_name="RAW_UPLOAD_TEST",
            rows_loaded=rows_loaded,
        ),
    )


def test_upload_requires_session_header(client: TestClient) -> None:
    response = post_upload(client, None, CSV_CONTENT)

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_upload_rejects_invalid_session(client: TestClient) -> None:
    response = post_upload(client, "mf_demo_missing", CSV_CONTENT)

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_upload_invalid_csv_fails(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_upload(client, session_id, b"not,csv\n1,2\n", file_name="sales.txt")

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_FILE_TYPE"


def test_upload_blocks_when_s3_not_configured(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_s3_readiness",
        lambda _config: not_configured_check("S3"),
    )
    session_id = create_session(client)

    response = post_upload(client, session_id, CSV_CONTENT)

    assert response.status_code == 400
    assert response.json()["error_code"] == "S3_NOT_READY"


def test_upload_blocks_when_snowflake_not_configured(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_s3_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_snowflake_readiness",
        lambda _config: not_configured_check("Snowflake"),
    )
    session_id = create_session(client)

    response = post_upload(client, session_id, CSV_CONTENT)

    assert response.status_code == 400
    assert response.json()["error_code"] == "SNOWFLAKE_NOT_READY"


def test_upload_success_creates_dataset_file_profile_and_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_ready_dependencies(monkeypatch, rows_loaded=2)
    session_id = create_session(client)

    response = post_upload(client, session_id, CSV_CONTENT)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["dataset"]["source_type"] == "uploaded_csv"
    assert body["dataset"]["status"] == "schema_review"
    assert body["dataset"]["row_count"] == 2
    assert body["dataset"]["column_count"] == 3
    assert body["dataset"]["raw_table_name"] == "RAW_UPLOAD_TEST"
    assert body["next_route"] == f"/demo/data-flow?datasetId={body['dataset']['id']}"
    assert [column["snowflake_column_name"] for column in body["schema_preview"]["columns"]] == [
        "ORDER_ID",
        "REVENUE",
        "ORDER_DATE",
    ]

    db_session.expire_all()
    assert len(db_session.scalars(select(Dataset)).all()) == 1
    assert len(db_session.scalars(select(DatasetFile)).all()) == 1
    profiles = db_session.scalars(select(ColumnProfile).order_by(ColumnProfile.column_index)).all()
    assert len(profiles) == 3
    assert profiles[0].detected_type == "identifier"
    assert profiles[1].detected_type == "decimal"
    session = db_session.get(DemoSession, session_id)
    assert session.successful_uploads_used == 1
    assert session.uploaded_datasets_used == 1
    assert session.total_upload_mb_used > 0


def test_upload_success_updates_workspace_and_limits(
    client: TestClient,
    monkeypatch,
) -> None:
    patch_ready_dependencies(monkeypatch, rows_loaded=2)
    session_id = create_session(client)
    upload_response = post_upload(client, session_id, CSV_CONTENT)
    dataset_id = upload_response.json()["dataset"]["id"]

    workspace_response = client.get(
        "/api/v1/workspace",
        headers={DEMO_SESSION_HEADER: session_id},
    )
    limits_response = client.get(
        "/api/v1/limits",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert [dataset["id"] for dataset in workspace["datasets"]] == [dataset_id]
    assert workspace["ready_datasets"] == []
    assert workspace["dashboard"]["cards"] == []
    assert workspace["history"]["analysis_runs"] == []
    assert limits_response.status_code == 200
    assert limits_response.json()["usage"]["uploaded_datasets_used"] == 1


def test_dataset_detail_returns_schema_preview(client: TestClient, monkeypatch) -> None:
    patch_ready_dependencies(monkeypatch, rows_loaded=2)
    session_id = create_session(client)
    upload_response = post_upload(client, session_id, CSV_CONTENT)
    dataset_id = upload_response.json()["dataset"]["id"]

    response = client.get(
        f"/api/v1/datasets/{dataset_id}",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]["id"] == dataset_id
    assert len(body["schema_preview"]["columns"]) == 3


def test_failed_s3_upload_does_not_create_dataset_or_increment_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_s3_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_snowflake_readiness",
        lambda _config: ready_check(),
    )

    def fail_upload(**_kwargs):
        raise storage_service.StorageServiceError("nope")

    monkeypatch.setattr(
        "app.services.dataset_service.storage_service.upload_csv_to_s3",
        fail_upload,
    )
    session_id = create_session(client)

    response = post_upload(client, session_id, CSV_CONTENT)

    assert response.status_code == 502
    assert response.json()["error_code"] == "S3_UPLOAD_FAILED"
    db_session.expire_all()
    assert db_session.scalars(select(Dataset)).all() == []
    assert db_session.get(DemoSession, session_id).uploaded_datasets_used == 0


def test_failed_snowflake_load_rolls_back_s3_and_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_s3_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_snowflake_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.storage_service.upload_csv_to_s3",
        lambda **_kwargs: storage_service.StorageUploadResult(
            storage_key="meshflow-demo/sessions/session/raw/dataset/sales.csv",
            storage_uri="s3://bucket/meshflow-demo/sessions/session/raw/dataset/sales.csv",
        ),
    )

    def fail_load(**_kwargs):
        raise snowflake_service.SnowflakeServiceError("copy failed")

    deleted_keys: list[str] = []
    monkeypatch.setattr(
        "app.services.dataset_service.snowflake_service.create_and_load_raw_table",
        fail_load,
    )
    monkeypatch.setattr(
        "app.services.dataset_service.storage_service.delete_s3_object",
        lambda *, storage_key, config: deleted_keys.append(storage_key),
    )
    session_id = create_session(client)

    response = post_upload(client, session_id, CSV_CONTENT)

    assert response.status_code == 502
    assert response.json()["error_code"] == "SNOWFLAKE_RAW_LOAD_FAILED"
    assert deleted_keys == ["meshflow-demo/sessions/session/raw/dataset/sales.csv"]
    db_session.expire_all()
    assert db_session.scalars(select(Dataset)).all() == []
    assert db_session.get(DemoSession, session_id).uploaded_datasets_used == 0


def test_preflight_still_does_not_increment_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.upload_preflight_service.readiness_service.check_s3_readiness",
        lambda _config: ready_check(),
    )
    monkeypatch.setattr(
        "app.services.upload_preflight_service.readiness_service.check_snowflake_readiness",
        lambda _config: ready_check(),
    )
    session_id = create_session(client)

    response = client.post(
        "/api/v1/datasets/upload/preflight",
        headers={DEMO_SESSION_HEADER: session_id},
        files={"file": ("sales.csv", CSV_CONTENT, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["can_upload"] is True
    db_session.expire_all()
    session = db_session.get(DemoSession, session_id)
    assert session.uploaded_datasets_used == 0
    assert session.total_upload_mb_used == 0


def test_upload_quota_blocks_second_uploaded_csv(client: TestClient, monkeypatch) -> None:
    patch_ready_dependencies(monkeypatch, rows_loaded=2)
    session_id = create_session(client)
    first_response = post_upload(client, session_id, CSV_CONTENT)
    assert first_response.status_code == 200

    second_response = post_upload(client, session_id, CSV_CONTENT)

    assert second_response.status_code == 400
    assert second_response.json()["error_code"] == "UPLOAD_LIMIT_REACHED"


def test_duplicate_normalized_headers_are_rejected_before_upload(
    client: TestClient,
    monkeypatch,
) -> None:
    patch_ready_dependencies(monkeypatch, rows_loaded=1)
    session_id = create_session(client)

    response = post_upload(client, session_id, b"Order ID,order-id\n1,2\n")

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_CSV_FORMAT"
