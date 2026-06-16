from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.services.demo_session_service import DEMO_SESSION_HEADER


def _force_missing_external_config(monkeypatch) -> None:
    for name in (
        "aws_region",
        "aws_s3_bucket",
        "s3_bucket_name",
        "aws_access_key_id",
        "aws_secret_access_key",
        "snowflake_account",
        "snowflake_user",
        "snowflake_password",
        "snowflake_role",
        "snowflake_warehouse",
        "snowflake_database",
        "snowflake_schema",
        "snowflake_stage_name",
        "openai_api_key",
        "openai_model",
        "gemini_api_key_1",
        "gemini_api_key_2",
        "gemini_api_key_3",
        "gemini_model_1",
        "gemini_model_2",
        "gemini_model_3",
    ):
        monkeypatch.setattr(settings, name, None)
    monkeypatch.setattr(settings, "allow_demo_reset_usage", False)


def test_phase10a_no_credentials_api_smoke(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    _force_missing_external_config(monkeypatch)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    created = client.post("/api/v1/demo-sessions")
    assert created.status_code == 200
    session_id = created.json()["session"]["id"]
    headers = {DEMO_SESSION_HEADER: session_id}

    current = client.get("/api/v1/demo-sessions/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["session"]["status"] == "active"

    workspace = client.get("/api/v1/workspace", headers=headers)
    assert workspace.status_code == 200
    workspace_body = workspace.json()
    assert workspace_body["datasets"] == []
    assert workspace_body["ready_datasets"] == []
    assert workspace_body["dashboard"]["cards"] == []
    assert workspace_body["history"]["analysis_runs"] == []

    limits = client.get("/api/v1/limits", headers=headers)
    assert limits.status_code == 200
    limits_body = limits.json()["limits"]
    assert limits_body["retention_days"] == 3
    assert limits_body["max_successful_analysis_runs_per_session"] == 8
    assert limits_body["max_dashboard_cards_per_session"] == 8

    preflight = client.post(
        "/api/v1/datasets/upload/preflight",
        headers=headers,
        files={"file": ("sales.csv", b"order_id,revenue\n1,10\n", "text/csv")},
    )
    assert preflight.status_code == 200
    preflight_body = preflight.json()
    assert preflight_body["can_upload"] is False
    assert preflight_body["readiness"]["s3"]["status"] == "not_configured"
    assert preflight_body["readiness"]["snowflake"]["status"] == "not_configured"

    demo = client.post("/api/v1/datasets/demo-retail", headers=headers)
    assert demo.status_code == 400
    assert demo.json()["error_code"] == "S3_NOT_READY"
    assert db_session.query(Dataset).count() == 0

    analysis = client.post(
        "/api/v1/analysis-runs",
        headers=headers,
        json={"attached_dataset_id": "missing", "question": "How is revenue performing?"},
    )
    assert analysis.status_code == 404
    assert analysis.json()["error_code"] == "DATASET_NOT_FOUND"

    reset = client.post("/api/v1/demo-sessions/reset", headers=headers)
    assert reset.status_code == 200
    reset_body = reset.json()
    assert reset_body["usage_reset"] is False
    assert reset_body["quota_restored"] is False

    delete_preflight = client.options(
        "/api/v1/datasets/missing",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "X-Demo-Session-Id",
        },
    )
    assert delete_preflight.status_code == 200
    assert "DELETE" in delete_preflight.headers["access-control-allow-methods"]
