from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_dataset_id() -> str:
    return f"ds_{uuid4().hex}"


def generate_dataset_file_id() -> str:
    return f"file_{uuid4().hex}"


def generate_column_profile_id() -> str:
    return f"col_{uuid4().hex}"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_dataset_id,
    )
    demo_session_id: Mapped[str] = mapped_column(
        ForeignKey("demo_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    raw_table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    files: Mapped[list[DatasetFile]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    column_profiles: Mapped[list[ColumnProfile]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="ColumnProfile.column_index",
    )


class DatasetFile(Base):
    __tablename__ = "dataset_files"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_dataset_file_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="files")
    column_profiles: Mapped[list[ColumnProfile]] = relationship(
        back_populates="dataset_file",
        cascade="all, delete-orphan",
    )


class ColumnProfile(Base):
    __tablename__ = "column_profiles"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_column_profile_id,
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    column_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    snowflake_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_type: Mapped[str] = mapped_column(String(32), nullable=False)
    null_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    null_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_values_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parse_stats_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    dataset: Mapped[Dataset] = relationship(back_populates="column_profiles")
    dataset_file: Mapped[DatasetFile | None] = relationship(back_populates="column_profiles")
