from fastapi import APIRouter, Depends, File, Header, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dataset import (
    DatasetDataFlowResponse,
    DatasetDetailResponse,
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetTransformRequest,
    DatasetTransformResponse,
    DatasetUploadResponse,
    SchemaPreview,
    SemanticColumnMappingPatchRequest,
    SemanticPreparationResponse,
    SemanticPreparationRunRequest,
)
from app.schemas.upload_preflight import UploadPreflightResponse
from app.services.demo_session_service import DEMO_SESSION_HEADER
from app.services.dataset_service import (
    create_raw_retail_demo_dataset,
    delete_dataset,
    get_dataset_detail,
    get_dataset_profile,
    list_datasets,
    upload_dataset,
)
from app.services.dbt_transformation_service import (
    get_dataset_data_flow,
    transform_dataset,
)
from app.services.semantic_preparation_service import (
    get_semantic_preparation,
    run_semantic_preparation,
    start_semantic_preparation,
    update_semantic_column_mappings,
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


@router.delete("/{dataset_id}", response_model=DatasetDeleteResponse)
def remove_dataset(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetDeleteResponse:
    return delete_dataset(db, demo_session_id, dataset_id)


@router.get("/{dataset_id}/profile", response_model=SchemaPreview)
def get_profile(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> SchemaPreview:
    return get_dataset_profile(db, demo_session_id, dataset_id)


@router.get("/{dataset_id}/semantic-preparation", response_model=SemanticPreparationResponse)
def get_dataset_semantic_preparation(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> SemanticPreparationResponse:
    return get_semantic_preparation(db, demo_session_id, dataset_id)


@router.post("/{dataset_id}/semantic-preparation", response_model=SemanticPreparationResponse)
def run_dataset_semantic_preparation(
    dataset_id: str,
    request: SemanticPreparationRunRequest | None = None,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> SemanticPreparationResponse:
    if request is None or request.async_run:
        return start_semantic_preparation(
            db,
            demo_session_id,
            dataset_id,
            force=request.force if request else False,
        )
    return run_semantic_preparation(
        db,
        demo_session_id,
        dataset_id,
        force=request.force if request else False,
    )


@router.patch("/{dataset_id}/semantic-columns", response_model=SemanticPreparationResponse)
def patch_dataset_semantic_columns(
    dataset_id: str,
    request: SemanticColumnMappingPatchRequest,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> SemanticPreparationResponse:
    return update_semantic_column_mappings(db, demo_session_id, dataset_id, request)


@router.get("/{dataset_id}/transformation", response_model=DatasetDataFlowResponse)
def get_dataset_transformation(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetDataFlowResponse:
    return get_dataset_data_flow(db, demo_session_id, dataset_id)


@router.get("/{dataset_id}/data-flow", response_model=DatasetDataFlowResponse)
def get_dataset_flow(
    dataset_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetDataFlowResponse:
    return get_dataset_data_flow(db, demo_session_id, dataset_id)


@router.post("/{dataset_id}/transform", response_model=DatasetTransformResponse)
def run_dataset_transform(
    dataset_id: str,
    request: DatasetTransformRequest | None = None,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetTransformResponse:
    return transform_dataset(
        db,
        demo_session_id,
        dataset_id,
        force=request.force if request else False,
    )


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


@router.post("/demo-retail", response_model=DatasetUploadResponse)
def create_demo_retail_dataset(
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    return create_raw_retail_demo_dataset(db, demo_session_id)
