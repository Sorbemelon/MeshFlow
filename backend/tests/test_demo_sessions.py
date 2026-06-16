from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.demo_session import DemoSession
from app.services.demo_session_service import DEMO_SESSION_HEADER, mark_expired_sessions


def create_session(client: TestClient) -> dict[str, object]:
    response = client.post("/api/v1/demo-sessions")
    assert response.status_code == 200
    return response.json()


def test_create_session_succeeds(client: TestClient) -> None:
    body = create_session(client)

    session = body["session"]
    assert session["id"].startswith("mf_demo_")
    assert session["status"] == "active"
    assert session["retention_days"] == 3
    assert body["limits"]["max_successful_analysis_runs_per_session"] == 8
    assert body["limits"]["max_dashboard_cards_per_session"] == 8
    assert body["usage"]["successful_analysis_runs_used"] == 0


def test_current_session_succeeds_with_valid_header(client: TestClient) -> None:
    created = create_session(client)
    session_id = created["session"]["id"]

    response = client.get(
        "/api/v1/demo-sessions/current",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == session_id
    assert body["session"]["status"] == "active"
    assert body["limits"]["max_successful_analysis_runs_per_session"] == 8


def test_current_session_requires_session_header(client: TestClient) -> None:
    response = client.get("/api/v1/demo-sessions/current")

    assert response.status_code == 400
    assert response.json() == {
        "status": "failed",
        "error_code": "SESSION_ID_REQUIRED",
        "failed_step": "demo_session",
        "message": "The X-Demo-Session-Id header is required for this workspace request.",
        "next_action": "Start a new demo session and retry with the returned session id.",
    }


def test_current_session_fails_for_invalid_session_id(client: TestClient) -> None:
    response = client.get(
        "/api/v1/demo-sessions/current",
        headers={DEMO_SESSION_HEADER: "mf_demo_missing"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "SESSION_NOT_FOUND"
    assert body["failed_step"] == "demo_session"


def test_current_session_marks_and_reports_expired_session(
    client: TestClient,
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    expired_session = DemoSession(
        status="active",
        created_at=now - timedelta(days=4),
        expires_at=now - timedelta(minutes=1),
        last_seen_at=now - timedelta(days=1),
    )
    db_session.add(expired_session)
    db_session.commit()
    db_session.refresh(expired_session)

    response = client.get(
        "/api/v1/demo-sessions/current",
        headers={DEMO_SESSION_HEADER: expired_session.id},
    )

    assert response.status_code == 410
    assert response.json()["error_code"] == "SESSION_EXPIRED"
    db_session.expire_all()
    assert db_session.get(DemoSession, expired_session.id).status == "expired"


def test_workspace_returns_honest_empty_state(client: TestClient) -> None:
    created = create_session(client)
    session_id = created["session"]["id"]

    response = client.get("/api/v1/workspace", headers={DEMO_SESSION_HEADER: session_id})

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == session_id
    assert body["datasets"] == []
    assert body["ready_datasets"] == []
    assert body["active_dataset"] is None
    assert body["dashboard"]["dashboard_count"] == 1
    assert body["dashboard"]["cards"] == []
    assert body["dashboard"]["cards_used"] == 0
    assert body["dashboard"]["cards_limit"] == 8
    assert body["history"]["analysis_runs"] == []
    assert body["history"]["successful_analysis_runs_used"] == 0
    assert body["history"]["successful_analysis_runs_limit"] == 8
    assert body["setup_status"] == {
        "backend": "available",
        "storage": "not_checked",
        "warehouse": "not_checked",
        "dbt": "not_checked",
        "ai": "not_checked",
    }


def test_limits_endpoint_returns_corrected_public_limits(client: TestClient) -> None:
    response = client.get("/api/v1/limits")

    assert response.status_code == 200
    body = response.json()
    limits = body["limits"]
    assert body["usage"] is None
    assert limits["retention_days"] == 3
    assert limits["max_demo_datasets_per_session"] == 1
    assert limits["max_uploaded_datasets_per_session"] == 1
    assert limits["max_upload_file_size_mb"] == 5
    assert limits["max_total_upload_size_mb"] == 10
    assert limits["max_successful_analysis_runs_per_session"] == 8
    assert limits["max_dashboard_cards_per_session"] == 8
    assert limits["preferred_charts_per_analysis"] == 1
    assert limits["max_charts_per_analysis"] == 3
    assert limits["dashboards_per_session"] == 1


def test_reset_does_not_reset_usage_by_default(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "allow_demo_reset_usage", False)
    created = create_session(client)
    session_id = created["session"]["id"]

    session = db_session.get(DemoSession, session_id)
    session.successful_analysis_runs_used = 4
    session.dashboard_cards_used = 4
    db_session.commit()

    response = client.post(
        "/api/v1/demo-sessions/reset",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["usage_reset"] is False
    assert body["session"]["status"] == "reset"
    assert body["usage"]["successful_analysis_runs_used"] == 4
    assert body["usage"]["dashboard_cards_used"] == 4


def test_reset_may_reset_usage_when_enabled(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "allow_demo_reset_usage", True)
    created = create_session(client)
    session_id = created["session"]["id"]

    session = db_session.get(DemoSession, session_id)
    session.successful_analysis_runs_used = 3
    session.dashboard_cards_used = 3
    session.total_upload_mb_used = 5
    db_session.commit()

    response = client.post(
        "/api/v1/demo-sessions/reset",
        headers={DEMO_SESSION_HEADER: session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["usage_reset"] is True
    assert body["usage"]["successful_analysis_runs_used"] == 0
    assert body["usage"]["dashboard_cards_used"] == 0
    assert body["usage"]["total_upload_mb_used"] == 0


def test_cleanup_foundation_marks_expired_sessions(db_session: Session) -> None:
    now = datetime.now(UTC)
    expired_session = DemoSession(
        status="active",
        created_at=now - timedelta(days=4),
        expires_at=now - timedelta(seconds=1),
        last_seen_at=now - timedelta(days=1),
    )
    active_session = DemoSession(
        status="active",
        created_at=now,
        expires_at=now + timedelta(days=3),
        last_seen_at=now,
    )
    db_session.add_all([expired_session, active_session])
    db_session.commit()

    expired_count = mark_expired_sessions(db_session, now)

    assert expired_count == 1
    db_session.expire_all()
    assert db_session.get(DemoSession, expired_session.id).status == "expired"
    assert db_session.get(DemoSession, active_session.id).status == "active"
