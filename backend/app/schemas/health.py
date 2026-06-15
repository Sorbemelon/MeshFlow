from typing import Literal

from pydantic import BaseModel


HealthStatus = Literal["ok", "degraded", "failed"]


class HealthResponse(BaseModel):
    status: HealthStatus
    service: str
    environment: str
    version: str


class DatabaseHealthResponse(BaseModel):
    status: HealthStatus
    database: str
    message: str
