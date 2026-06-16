from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demo_session import DemoSession
from app.schemas.upload_preflight import ReadinessCheck
from app.services.demo_session_service import DEMO_SESSION_HEADER


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()["session"]["id"]


def post_preflight(
    client: TestClient,
    session_id: str | None,
    content: bytes,
    *,
    file_name: str = "sales.csv",
) -> object:
    headers = {DEMO_SESSION_HEADER: session_id} if session_id else {}
    return client.post(
        "/api/v1/datasets/upload/preflight",
        headers=headers,
        files={"file": (file_name, content, "text/csv")},
    )


def ready_check() -> ReadinessCheck:
    return ReadinessCheck(
        status="ready",
        message="Readiness check passed.",
        next_action=None,
    )


def not_configured_check(name: str) -> ReadinessCheck:
    return ReadinessCheck(
        status="not_configured",
        message=f"{name} is not configured.",
        next_action=f"Set {name} configuration before enabling uploads.",
    )


def test_upload_preflight_requires_session_header(client: TestClient) -> None:
    response = post_preflight(client, None, b"order_id,revenue\n1,10\n")

    assert response.status_code == 400
    assert response.json()["error_code"] == "SESSION_ID_REQUIRED"


def test_upload_preflight_rejects_invalid_session(client: TestClient) -> None:
    response = post_preflight(client, "mf_demo_missing", b"order_id,revenue\n1,10\n")

    assert response.status_code == 404
    assert response.json()["error_code"] == "SESSION_NOT_FOUND"


def test_valid_csv_with_missing_readiness_config_is_blocked(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.upload_preflight_service.readiness_service.check_s3_readiness",
        lambda _config: not_configured_check("S3"),
    )
    monkeypatch.setattr(
        "app.services.upload_preflight_service.readiness_service.check_snowflake_readiness",
        lambda _config: not_configured_check("Snowflake"),
    )
    session_id = create_session(client)

    response = post_preflight(client, session_id, b"order_id,revenue\n1,10\n")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["can_upload"] is False
    assert body["file"]["valid"] is True
    assert body["readiness"]["s3"]["status"] == "not_configured"
    assert body["readiness"]["snowflake"]["status"] == "not_configured"


def test_valid_csv_with_ready_checks_can_upload(
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

    response = post_preflight(client, session_id, b"order_id,revenue\n1,10\n")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["can_upload"] is True
    assert body["file"]["headers"] == ["order_id", "revenue"]
    db_session.expire_all()
    session = db_session.get(DemoSession, session_id)
    assert session.uploaded_datasets_used == 0
    assert session.total_upload_mb_used == 0


def test_invalid_extension_is_blocked_without_usage_increment(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)

    response = post_preflight(
        client,
        session_id,
        b"order_id,revenue\n1,10\n",
        file_name="sales.txt",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["can_upload"] is False
    assert "INVALID_FILE_TYPE" in body["file"]["errors"]
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).uploaded_datasets_used == 0


def test_empty_file_is_blocked(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_preflight(client, session_id, b"")

    assert response.status_code == 200
    assert "INVALID_CSV_FORMAT" in response.json()["file"]["errors"]


def test_empty_header_is_blocked(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_preflight(client, session_id, b",revenue\n1,10\n")

    assert response.status_code == 200
    body = response.json()
    assert body["file"]["valid"] is False
    assert "INVALID_CSV_FORMAT" in body["file"]["errors"]


def test_duplicate_normalized_headers_are_blocked(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_preflight(client, session_id, b"Order ID,order-id\n1,10\n")

    assert response.status_code == 200
    assert "INVALID_CSV_FORMAT" in response.json()["file"]["errors"]


def test_one_column_csv_is_blocked(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_preflight(client, session_id, b"order_id\n1\n")

    assert response.status_code == 200
    assert "INVALID_CSV_FORMAT" in response.json()["file"]["errors"]


def test_no_data_rows_is_blocked(client: TestClient) -> None:
    session_id = create_session(client)

    response = post_preflight(client, session_id, b"order_id,revenue\n")

    assert response.status_code == 200
    assert "INVALID_CSV_FORMAT" in response.json()["file"]["errors"]


def test_oversized_file_is_blocked(client: TestClient) -> None:
    session_id = create_session(client)
    oversized = b"order_id,revenue\n" + (b"1,10\n" * (1024 * 1024 + 1))

    response = post_preflight(client, session_id, oversized)

    assert response.status_code == 200
    body = response.json()
    assert body["can_upload"] is False
    assert "FILE_TOO_LARGE" in body["file"]["errors"]


def test_upload_quota_already_used_is_blocked(
    client: TestClient,
    db_session: Session,
) -> None:
    session_id = create_session(client)
    session = db_session.get(DemoSession, session_id)
    session.uploaded_datasets_used = 1
    db_session.commit()

    response = post_preflight(client, session_id, b"order_id,revenue\n1,10\n")

    assert response.status_code == 200
    body = response.json()
    assert body["can_upload"] is False
    assert "UPLOAD_LIMIT_REACHED" in body["quota"]["errors"]
    db_session.expire_all()
    assert db_session.get(DemoSession, session_id).uploaded_datasets_used == 1


def test_readiness_failure_does_not_increment_usage(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.upload_preflight_service.readiness_service.check_s3_readiness",
        lambda _config: not_configured_check("S3"),
    )
    monkeypatch.setattr(
        "app.services.upload_preflight_service.readiness_service.check_snowflake_readiness",
        lambda _config: ready_check(),
    )
    session_id = create_session(client)

    response = post_preflight(client, session_id, b"order_id,revenue\n1,10\n")

    assert response.status_code == 200
    assert response.json()["can_upload"] is False
    db_session.expire_all()
    session = db_session.get(DemoSession, session_id)
    assert session.uploaded_datasets_used == 0
    assert session.total_upload_mb_used == 0
