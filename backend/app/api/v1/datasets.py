from fastapi import APIRouter, Depends, File, Header, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dataset import (
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetUploadResponse,
    SchemaPreview,
)
from app.schemas.upload_preflight import UploadPreflightResponse
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.dataset_service import (
    get_dataset_detail,
    get_dataset_profile,
    list_datasets,
    upload_dataset,
)
from app.services.upload_preflight_service import run_upload_preflight

router = APIRouter()


@router.get("", response_model=DatasetListResponse)
def get_datasets(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetListResponse:
    return list_datasets(db, demo_session_id)


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetDetailResponse:
    return get_dataset_detail(db, demo_session_id, dataset_id)


@router.get("/{dataset_id}/profile", response_model=SchemaPreview)
def get_profile(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> SchemaPreview:
    return get_dataset_profile(db, demo_session_id, dataset_id)


@router.post("/upload/preflight", response_model=UploadPreflightResponse)
async def upload_preflight(
    file: UploadFile | None = File(default=None),
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> UploadPreflightResponse:
    return await run_upload_preflight(db, demo_session_id, file)


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_csv_dataset(
    file: UploadFile | None = File(default=None),
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    return await upload_dataset(db, demo_session_id, file)
