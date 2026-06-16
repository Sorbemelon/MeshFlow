from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.limits import LimitsResponse
from app.services.demo_session_service import DEMO_SESSION_HEADER, get_limits_response

router = APIRouter()


@router.get("", response_model=LimitsResponse)
def get_limits(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> LimitsResponse:
    return get_limits_response(db, demo_session_id)
