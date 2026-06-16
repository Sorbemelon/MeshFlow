from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import (
    AnalysisRunCreateRequest,
    AnalysisRunListResponse,
    AnalysisRunResponse,
)
from app.services.analysis_run_service import (
    create_analysis_run,
    get_analysis_run_detail,
    list_analysis_runs,
)
from app.services.demo_session_service import DEMO_SESSION_HEADER

router = APIRouter()


@router.post("", response_model=AnalysisRunResponse)
def create_analysis(
    request: AnalysisRunCreateRequest,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> AnalysisRunResponse:
    return create_analysis_run(db, demo_session_id, request)


@router.get("", response_model=AnalysisRunListResponse)
def get_analysis_runs(
    dataset_id: str | None = Query(default=None),
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> AnalysisRunListResponse:
    return list_analysis_runs(db, demo_session_id, dataset_id)


@router.get("/{analysis_run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(
    analysis_run_id: str,
    demo_session_id: str | None = Header(default=None, alias=DEMO_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> AnalysisRunResponse:
    return get_analysis_run_detail(db, demo_session_id, analysis_run_id)
