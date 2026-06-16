from fastapi import APIRouter

from app.api.v1 import analysis_runs, dashboard, datasets, demo_sessions, health, limits, workspace

api_router = APIRouter()
api_router.include_router(analysis_runs.router, prefix="/analysis-runs", tags=["analysis-runs"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(demo_sessions.router, prefix="/demo-sessions", tags=["demo-sessions"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(limits.router, prefix="/limits", tags=["limits"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
