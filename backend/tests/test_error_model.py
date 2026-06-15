from fastapi import status

from app.core.errors import AppError


def test_app_error_serializes_honest_failure_response() -> None:
    error = AppError(
        error_code="SNOWFLAKE_NOT_READY",
        failed_step="warehouse_readiness",
        message="Snowflake is not configured.",
        next_action="Check Snowflake environment variables and try again.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )

    response = error.to_response().model_dump()

    assert response == {
        "status": "failed",
        "error_code": "SNOWFLAKE_NOT_READY",
        "failed_step": "warehouse_readiness",
        "message": "Snowflake is not configured.",
        "next_action": "Check Snowflake environment variables and try again.",
    }
