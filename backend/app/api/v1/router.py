from fastapi import APIRouter

from app.api.v1 import demo_sessions, health, limits, workspace

api_router = APIRouter()
api_router.include_router(demo_sessions.router, prefix="/demo-sessions", tags=["demo-sessions"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(limits.router, prefix="/limits", tags=["limits"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
