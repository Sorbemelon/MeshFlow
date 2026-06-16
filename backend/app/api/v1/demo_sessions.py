from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.demo_session import DemoSessionResetResponse, DemoSessionResponse
from app.services.demo_session_service import (
    DEMO_SESSION_HEADER,
    create_demo_session,
    get_current_session_response,
    reset_demo_session,
)

router = APIRouter()


@router.post("", response_model=DemoSessionResponse)
def create_session(db: Session = Depends(get_db)) -> DemoSessionResponse:
    return create_demo_session(db)


@router.get("/current", response_model=DemoSessionResponse)
def get_current_session(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DemoSessionResponse:
    return get_current_session_response(db, demo_session_id)


@router.post("/reset", response_model=DemoSessionResetResponse)
def reset_session(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DemoSessionResetResponse:
    return reset_demo_session(db, demo_session_id)
