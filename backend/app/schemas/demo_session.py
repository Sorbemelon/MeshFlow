from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.limits import DemoLimits, DemoUsage


SessionStatus = Literal["active", "expired", "reset"]


class DemoSessionSummary(BaseModel):
    id: str
    status: SessionStatus
    created_at: datetime
    expires_at: datetime
    retention_days: int


class DemoSessionResponse(BaseModel):
    session: DemoSessionSummary
    limits: DemoLimits
    usage: DemoUsage


class DemoSessionResetResponse(BaseModel):
    session: DemoSessionSummary
    limits: DemoLimits
    usage: DemoUsage
    usage_reset: bool
    message: str
