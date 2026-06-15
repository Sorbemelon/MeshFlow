from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.health import DatabaseHealthResponse, HealthResponse


def app_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )


def database_health(db: Session) -> DatabaseHealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return DatabaseHealthResponse(
            status="failed",
            database="metadata",
            message=f"Metadata database check failed: {exc.__class__.__name__}",
        )

    return DatabaseHealthResponse(
        status="ok",
        database="metadata",
        message="Metadata database connection is healthy.",
    )
