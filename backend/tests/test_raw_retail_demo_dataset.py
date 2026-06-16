import csv

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import ColumnProfile, Dataset, DatasetFile
from app.models.demo_session import DemoSession
from app.schemas.upload_preflight import ReadinessCheck
from app.services import snowflake_service, storage_service
from app.services.dataset_service import (
    RAW_RETAIL_DEMO_FILE_NAME,
    RAW_RETAIL_DEMO_FIXTURE_PATH,
    RAW_RETAIL_DEMO_NAME,
    RAW_RETAIL_DEMO_SOURCE_TYPE,
)
from app.services.demo_session_service import DEMO_SESSION_HEADER


EXPECTED_RAW_RETAIL_COLUMNS = [
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


def post_demo(client: TestClient, session_id: str | None):
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.post("/api/v1/datasets/demo-retail", headers=headers)


def ready_check() -> ReadinessCheck:
    return ReadinessCheck(status="ready", message="Ready.", next_action=None)


def not_configured_check(name: str) -> ReadinessCheck:
    return ReadinessCheck(
        status="not_configured",
        message=f"{name} is not configured.",
        next_action=f"Set {name} configuration.",
    )


def fixture_row_count() -> int:
    with RAW_RETAIL_DEMO_FIXTURE_PATH.open(newline="", encoding="utf-8") as handle:
        return len(list(csv.DictReader(handle)))


def patch_ready_dependencies(monkeypatch, *, rows_loaded: int | None = None) -> None:
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
            storage_key="meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv",
            storage_uri="s3://bucket/meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv",
        ),
    )
    monkeypatch.setattr(
        "app.services.dataset_service.snowflake_service.create_and_load_raw_table",
        lambda **_kwargs: snowflake_service.SnowflakeLoadResult(
            raw_table_name="RAW_UPLOAD_DEMO_RETAIL",
            rows_loaded=rows_loaded if rows_loaded is not None else fixture_row_count(),
        ),
    )


def test_demo_creation_requires_session_header(client: TestClient) -> None:
    response = post_demo(client, None)

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_demo_creation_rejects_invalid_session(client: TestClient) -> None:
    response = post_demo(client, "mf_demo_missing")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_demo_creation_blocks_when_s3_not_configured(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.dataset_service.readiness_service.check_s3_readiness",
        lambda _config: not_configured_check("S3"),
    )
    session_id = create_session(client)

    response = post_demo(client, session_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "S3_NOT_READY"
    db_session.expire_all()
    assert db_session.scalars(select(Dataset)).all() == []
    assert db_session.get(DemoSession, session_id).demo_dataset_used == 0


def test_demo_creation_blocks_when_snowflake_not_configured(
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
        lambda _config: not_configured_check("Snowflake"),
    )
    session_id = create_session(client)

    response = post_demo(client, session_id)

    assert response.status_code == 400
    assert response.json()["error_code"] == "SNOWFLAKE_NOT_READY"
    db_session.expire_all()
    assert db_session.scalars(select(Dataset)).all() == []
    assert db_session.get(DemoSession, session_id).demo_dataset_used == 0


def test_demo_creation_success_creates_dataset_file_profile_and_demo_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    uploaded_kwargs: dict[str, object] = {}

    def upload_capture(**kwargs):
        uploaded_kwargs.update(kwargs)
        return storage_service.StorageUploadResult(
            storage_key="meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv",
            storage_uri="s3://bucket/meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv",
        )

    patch_ready_dependencies(monkeypatch)
    monkeypatch.setattr(
        "app.services.dataset_service.storage_service.upload_csv_to_s3",
        upload_capture,
    )
    session_id = create_session(client)

    response = post_demo(client, session_id)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["dataset"]["name"] == RAW_RETAIL_DEMO_NAME
    assert body["dataset"]["source_type"] == RAW_RETAIL_DEMO_SOURCE_TYPE
    assert body["dataset"]["status"] == "schema_review"
    assert body["dataset"]["row_count"] == fixture_row_count()
    assert body["dataset"]["column_count"] == len(EXPECTED_RAW_RETAIL_COLUMNS)
    assert body["file"]["file_name"] == RAW_RETAIL_DEMO_FILE_NAME
    assert body["next_route"] == f"/demo/data-flow?datasetId={body['dataset']['id']}"
    assert uploaded_kwargs["storage_group"] == "raw-demo"

    raw_columns = [
        column["raw_column_name"] for column in body["schema_preview"]["columns"]
    ]
    assert raw_columns == EXPECTED_RAW_RETAIL_COLUMNS

    db_session.expire_all()
    assert len(db_session.scalars(select(Dataset)).all()) == 1
    assert len(db_session.scalars(select(DatasetFile)).all()) == 1
    profiles = db_session.scalars(select(ColumnProfile)).all()
    assert len(profiles) == len(EXPECTED_RAW_RETAIL_COLUMNS)
    session = db_session.get(DemoSession, session_id)
    assert session.demo_dataset_used == 1
    assert session.uploaded_datasets_used == 0
    assert session.successful_uploads_used == 0
    assert session.total_upload_mb_used == 0


def test_demo_creation_updates_workspace_and_limits(
    client: TestClient,
    monkeypatch,
) -> None:
    patch_ready_dependencies(monkeypatch)
    session_id = create_session(client)
    upload_response = post_demo(client, session_id)
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
    assert workspace["datasets"][0]["source_type"] == RAW_RETAIL_DEMO_SOURCE_TYPE
    assert workspace["ready_datasets"] == []
    assert workspace["dashboard"]["cards"] == []
    assert workspace["history"]["analysis_runs"] == []
    assert limits_response.status_code == 200
    usage = limits_response.json()["usage"]
    assert usage["demo_dataset_used"] == 1
    assert usage["uploaded_datasets_used"] == 0


def test_demo_creation_twice_returns_existing_without_duplicate_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    patch_ready_dependencies(monkeypatch)
    session_id = create_session(client)
    first_response = post_demo(client, session_id)
    first_dataset_id = first_response.json()["dataset"]["id"]

    second_response = post_demo(client, session_id)

    assert second_response.status_code == 200
    body = second_response.json()
    assert body["status"] == "already_exists"
    assert body["dataset"]["id"] == first_dataset_id
    assert body["message"] == (
        "The Raw Retail Transactions Demo has already been added to this session."
    )
    db_session.expire_all()
    assert len(db_session.scalars(select(Dataset)).all()) == 1
    assert db_session.get(DemoSession, session_id).demo_dataset_used == 1


def test_failed_demo_s3_upload_does_not_create_dataset_or_increment_usage(
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

    response = post_demo(client, session_id)

    assert response.status_code == 502
    assert response.json()["error_code"] == "S3_UPLOAD_FAILED"
    db_session.expire_all()
    assert db_session.scalars(select(Dataset)).all() == []
    assert db_session.get(DemoSession, session_id).demo_dataset_used == 0


def test_failed_demo_snowflake_load_rolls_back_s3_and_usage(
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
            storage_key="meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv",
            storage_uri="s3://bucket/meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv",
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

    response = post_demo(client, session_id)

    assert response.status_code == 502
    assert response.json()["error_code"] == "SNOWFLAKE_RAW_LOAD_FAILED"
    assert deleted_keys == [
        "meshflow-demo/sessions/session/raw-demo/dataset/raw_retail_transactions_demo.csv"
    ]
    db_session.expire_all()
    assert db_session.scalars(select(Dataset)).all() == []
    assert db_session.get(DemoSession, session_id).demo_dataset_used == 0


def test_raw_retail_fixture_is_single_denormalized_input() -> None:
    fixture_files = sorted(RAW_RETAIL_DEMO_FIXTURE_PATH.parent.glob("*.csv"))
    assert fixture_files == [RAW_RETAIL_DEMO_FIXTURE_PATH]

    with RAW_RETAIL_DEMO_FIXTURE_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) >= 40
    assert list(rows[0].keys()) == EXPECTED_RAW_RETAIL_COLUMNS
    assert {"customer_name", "product_name", "store_name"} <= set(rows[0])
    assert not any(
        path.name.startswith(("customers", "products", "stores", "calendar"))
        for path in RAW_RETAIL_DEMO_FIXTURE_PATH.parent.glob("*.csv")
    )
