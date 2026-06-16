from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workspace import WorkspaceResponse
from app.services.demo_session_service import DEMO_SESSION_HEADER, get_workspace_response

router = APIRouter()


@router.get("", response_model=WorkspaceResponse)
def get_workspace(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    return get_workspace_response(db, demo_session_id)
