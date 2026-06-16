from fastapi import APIRouter, Depends, File, Header, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.upload_preflight import UploadPreflightResponse
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.upload_preflight_service import run_upload_preflight

router = APIRouter()


@router.post("/upload/preflight", response_model=UploadPreflightResponse)
async def upload_preflight(
    file: UploadFile | None = File(default=None),
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> UploadPreflightResponse:
    return await run_upload_preflight(db, demo_session_id, file)
