from typing import Literal

from pydantic import BaseModel, Field


PreflightStatus = Literal["ready", "blocked", "failed"]
ReadinessStatus = Literal["ready", "not_configured", "failed", "not_checked"]


class UploadFileValidation(BaseModel):
    file_name: str
    size_bytes: int
    size_mb: float
    extension: str
    detected_format: str | None
    valid: bool
    row_count_previewed: int
    column_count: int
    headers: list[str]
    warnings: list[str]
    errors: list[str]


class UploadQuotaSummary(BaseModel):
    uploaded_datasets_used: int
    uploaded_datasets_limit: int | None = None
    total_upload_mb_used: float
    total_upload_mb_limit: int
    file_size_mb_limit: int
    errors: list[str] = Field(default_factory=list)


class ReadinessCheck(BaseModel):
    status: ReadinessStatus
    message: str
    next_action: str | None = None


class UploadReadinessSummary(BaseModel):
    s3: ReadinessCheck
    snowflake: ReadinessCheck


class UploadPreflightResponse(BaseModel):
    status: PreflightStatus
    can_upload: bool
    file: UploadFileValidation
    quota: UploadQuotaSummary
    readiness: UploadReadinessSummary
    message: str
