from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import (
    DashboardCardCreateRequest,
    DashboardCardMutationResponse,
    DashboardResponse,
)
from app.services.dashboard_service import (
    archive_dashboard_card,
    create_dashboard_card_from_analysis_run,
    get_dashboard_response,
)
from app.services.demo_session_service import DEMO_SESSION_HEADER

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return get_dashboard_response(db, demo_session_id)


@router.post("/cards", response_model=DashboardCardMutationResponse)
def create_dashboard_card(
    request: DashboardCardCreateRequest,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DashboardCardMutationResponse:
    return create_dashboard_card_from_analysis_run(
        db,
        demo_session_id,
        request.analysis_run_id,
    )


@router.delete("/cards/{card_id}", response_model=DashboardCardMutationResponse)
def delete_dashboard_card(
    card_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DashboardCardMutationResponse:
    return archive_dashboard_card(db, demo_session_id, card_id)
