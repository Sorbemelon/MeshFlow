from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import DemoSession


@pytest.fixture(autouse=True)
def isolate_live_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests from using real local .env credentials or reset flags."""

    safe_overrides = {
        "app_env": "test",
        "allow_demo_reset_usage": False,
        "aws_region": None,
        "aws_s3_bucket": None,
        "s3_bucket_name": None,
        "aws_access_key_id": None,
        "aws_secret_access_key": None,
        "snowflake_account": None,
        "snowflake_user": None,
        "snowflake_password": None,
        "snowflake_role": None,
        "snowflake_warehouse": None,
        "snowflake_database": None,
        "snowflake_schema": None,
        "snowflake_stage_name": None,
        "openai_api_key": None,
        "gemini_api_key_1": None,
        "gemini_api_key_2": None,
        "gemini_api_key_3": None,
    }
    for field_name, value in safe_overrides.items():
        monkeypatch.setattr(settings, field_name, value)


@pytest.fixture()
def db_session_factory() -> Generator[sessionmaker[Session], None, None]:
    _ = DemoSession
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        class_=Session,
    )

    try:
        yield testing_session_factory
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    db = db_session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
