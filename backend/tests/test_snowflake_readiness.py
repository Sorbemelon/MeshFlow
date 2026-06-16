from app.core.config import Settings
from app.services import readiness_service, snowflake_service


def snowflake_settings() -> Settings:
    return Settings(
        _env_file=None,
        SNOWFLAKE_ACCOUNT="account",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="password",
        SNOWFLAKE_ROLE="role",
        SNOWFLAKE_WAREHOUSE="warehouse",
        SNOWFLAKE_DATABASE="analytics",
        SNOWFLAKE_SCHEMA="raw",
        SNOWFLAKE_STAGE_NAME="analytics.raw.meshflow_uploads",
    )


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.description = None

    def execute(self, sql: str) -> None:
        self.statements.append(sql)
        if sql.startswith("SHOW STAGES"):
            self.description = [("name",), ("url",)]
        else:
            self.description = None

    def fetchall(self) -> list[tuple[str, str]]:
        return [("MESHFLOW_UPLOADS", "s3://meshflow-test-bucket")]

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def close(self) -> None:
        self.closed = True


def test_check_connection_and_stage_supports_fully_qualified_stage(monkeypatch) -> None:
    connection = FakeConnection()
    monkeypatch.setattr(snowflake_service, "_connect", lambda _config: connection)

    snowflake_service.check_connection_and_stage(snowflake_settings())

    statements = connection.cursor_instance.statements
    assert statements[0] == "SELECT 1"
    assert statements[1] == 'SHOW STAGES LIKE \'MESHFLOW_UPLOADS\' IN SCHEMA "ANALYTICS"."RAW"'
    assert statements[2] == 'DESC STAGE "ANALYTICS"."RAW"."MESHFLOW_UPLOADS"'
    assert connection.closed is True


def test_snowflake_readiness_surfaces_safe_stage_diagnostic(monkeypatch) -> None:
    monkeypatch.setattr(
        snowflake_service,
        "check_connection_and_stage",
        lambda _config: (_ for _ in ()).throw(
            snowflake_service.SnowflakeServiceError(
                "Snowflake stage was not found or the configured role lacks access."
            )
        ),
    )

    readiness = readiness_service.check_snowflake_readiness(snowflake_settings())

    assert readiness.status == "failed"
    assert readiness.message == "Snowflake stage was not found or the configured role lacks access."
    assert "SNOWFLAKE_STAGE_NAME" in readiness.next_action


def test_check_connection_and_stage_rejects_non_s3_stage(monkeypatch) -> None:
    connection = FakeConnection()
    monkeypatch.setattr(snowflake_service, "_connect", lambda _config: connection)
    monkeypatch.setattr(connection.cursor_instance, "fetchall", lambda: [("MESHFLOW_UPLOADS", "")])

    try:
        snowflake_service.check_connection_and_stage(snowflake_settings())
    except snowflake_service.SnowflakeServiceError as exc:
        assert str(exc) == "Snowflake stage was found, but it is not an external S3 stage."
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SnowflakeServiceError")


def test_raw_load_rejects_zero_loaded_rows(monkeypatch) -> None:
    class FakeLoadCursor:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, sql: str) -> None:
            self.statements.append(sql)

        def fetchone(self) -> tuple[int]:
            return (0,)

        def close(self) -> None:
            pass

    class FakeLoadConnection:
        def __init__(self) -> None:
            self.cursor_instance = FakeLoadCursor()

        def cursor(self) -> FakeLoadCursor:
            return self.cursor_instance

        def close(self) -> None:
            pass

    connection = FakeLoadConnection()
    monkeypatch.setattr(snowflake_service, "_connect", lambda _config: connection)

    try:
        snowflake_service.create_and_load_raw_table(
            dataset_id="ds_zero_rows",
            snowflake_columns=["ORDER_ID"],
            storage_key="meshflow-demo/sessions/session/raw/file.csv",
            config=snowflake_settings(),
        )
    except snowflake_service.SnowflakeServiceError as exc:
        assert str(exc) == "Snowflake raw load completed but loaded zero rows."
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SnowflakeServiceError")

    assert any(statement.startswith("DROP TABLE IF EXISTS") for statement in connection.cursor_instance.statements)
