from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_demo_session_id() -> str:
    return f"mf_demo_{token_urlsafe(18)}"


class DemoSession(Base):
    __tablename__ = "demo_sessions"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_demo_session_id,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    successful_uploads_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    demo_dataset_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_datasets_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_analysis_runs_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dashboard_cards_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_upload_mb_used: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_from_ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
