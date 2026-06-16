from typing import Literal

from pydantic import BaseModel


DatasetSourceType = Literal["uploaded_csv", "demo_raw_retail_later"]
DatasetStatus = Literal["schema_review", "warehouse_loaded", "failed", "deleted"]
DetectedColumnType = Literal[
    "date",
    "integer",
    "decimal",
    "boolean",
    "string",
    "identifier",
    "unknown",
]


class ColumnProfileSummary(BaseModel):
    column_index: int
    raw_column_name: str
    normalized_column_name: str
    snowflake_column_name: str
    detected_type: DetectedColumnType
    null_count: int
    null_rate: float
    unique_count: int | None = None
    sample_values: list[str]


class SchemaPreview(BaseModel):
    columns: list[ColumnProfileSummary]


class DatasetSummary(BaseModel):
    id: str
    name: str
    source_type: DatasetSourceType
    status: DatasetStatus
    row_count: int
    column_count: int
    raw_table_name: str
    created_at: str


class DatasetFileSummary(BaseModel):
    file_name: str
    size_bytes: int
    storage_key: str
    checksum_sha256: str | None = None


class DatasetDetailResponse(BaseModel):
    dataset: DatasetSummary
    file: DatasetFileSummary | None = None
    schema_preview: SchemaPreview


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class DatasetUploadResponse(BaseModel):
    status: Literal["uploaded"]
    dataset: DatasetSummary
    file: DatasetFileSummary
    schema_preview: SchemaPreview
    next_route: str
