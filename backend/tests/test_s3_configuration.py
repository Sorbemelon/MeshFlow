from types import SimpleNamespace

from app.core.config import Settings
from app.services import readiness_service, storage_service


def s3_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "AWS_REGION": "us-east-1",
        "S3_BUCKET_NAME": "canonical-bucket",
        "S3_UPLOAD_PREFIX": "meshflow-test",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
    }
    values.update(overrides)
    return Settings(**values)


def test_s3_bucket_name_loads_canonical_setting() -> None:
    settings = s3_settings(S3_BUCKET_NAME="meshflow-canonical")

    assert settings.s3_bucket_name == "meshflow-canonical"


def test_s3_readiness_missing_bucket_reports_not_configured() -> None:
    readiness = readiness_service.check_s3_readiness(s3_settings(S3_BUCKET_NAME=None))

    assert readiness.status == "not_configured"
    assert "S3_BUCKET_NAME" in readiness.next_action


def test_s3_readiness_uses_canonical_bucket(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class FakeS3Client:
        def head_bucket(self, *, Bucket: str) -> None:
            calls.append(("head_bucket", Bucket))

    monkeypatch.setattr(
        readiness_service,
        "boto3",
        SimpleNamespace(client=lambda *_args, **_kwargs: FakeS3Client()),
        raising=False,
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "boto3",
        SimpleNamespace(client=lambda *_args, **_kwargs: FakeS3Client()),
    )

    readiness = readiness_service.check_s3_readiness(s3_settings())

    assert readiness.status == "ready"
    assert calls == [("head_bucket", "canonical-bucket")]


def test_storage_upload_uses_canonical_bucket(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeS3Client:
        def put_object(self, **kwargs) -> None:
            calls.append(kwargs)

    monkeypatch.setitem(
        __import__("sys").modules,
        "boto3",
        SimpleNamespace(client=lambda *_args, **_kwargs: FakeS3Client()),
    )

    result = storage_service.upload_csv_to_s3(
        session_id="mf_demo_test",
        dataset_id="ds_test",
        file_name="sales.csv",
        content=b"order_id,revenue\n1,10\n",
        content_type="text/csv",
        config=s3_settings(),
    )

    assert calls[0]["Bucket"] == "canonical-bucket"
    assert result.storage_uri.startswith("s3://canonical-bucket/")


def test_storage_cleanup_uses_canonical_bucket(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeS3Client:
        def delete_object(self, **kwargs) -> None:
            calls.append(kwargs)

    monkeypatch.setitem(
        __import__("sys").modules,
        "boto3",
        SimpleNamespace(client=lambda *_args, **_kwargs: FakeS3Client()),
    )

    cleanup = storage_service.delete_s3_object_for_cleanup(
        storage_key="sessions/test/raw/ds/file.csv",
        config=s3_settings(),
    )

    assert cleanup.status == "completed"
    assert calls == [{"Bucket": "canonical-bucket", "Key": "sessions/test/raw/ds/file.csv"}]
