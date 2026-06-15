from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse
from app.services.health_service import app_health, database_health

router = APIRouter()


@router.get("", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return app_health()


@router.get("/db", response_model=DatabaseHealthResponse)
def get_database_health(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    return database_health(db)
