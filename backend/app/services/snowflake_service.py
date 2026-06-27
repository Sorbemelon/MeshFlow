from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from app.core.config import Settings, settings


class SnowflakeServiceError(Exception):
    pass


@dataclass
class SnowflakeLoadResult:
    raw_table_name: str
    rows_loaded: int


@dataclass
class SnowflakeQueryResult:
    output_schema: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    row_count: int


@dataclass(frozen=True)
class CleanupOperationResult:
    status: str
    warning: str | None = None


def raw_table_name_for_dataset(dataset_id: str) -> str:
    suffix = re.sub(r"[^A-Za-z0-9_]+", "_", dataset_id).upper()
    return f"RAW_UPLOAD_{suffix[:48]}"


def _quote_identifier(value: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", value):
        raise SnowflakeServiceError(f"Unsafe Snowflake identifier: {value!r}")
    return f'"{value.upper()}"'


def quote_identifier(value: str) -> str:
    return _quote_identifier(value)


def _quote_qualified_name(value: str) -> str:
    return ".".join(_quote_identifier(part.strip()) for part in value.split(".") if part.strip())


def quote_qualified_name(value: str) -> str:
    return _quote_qualified_name(value)


def _identifier_name(value: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", value):
        raise SnowflakeServiceError("Snowflake stage name contains an unsafe identifier.")
    return value.upper()


def _stage_lookup_parts(stage_name: str, config: Settings) -> tuple[str, str, str]:
    parts = [_identifier_name(part.strip()) for part in stage_name.split(".") if part.strip()]
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        if not config.snowflake_database:
            raise SnowflakeServiceError(
                "SNOWFLAKE_DATABASE is required when SNOWFLAKE_STAGE_NAME is schema-qualified."
            )
        return config.snowflake_database, parts[0], parts[1]
    if len(parts) == 1:
        if not config.snowflake_database or not config.snowflake_schema:
            raise SnowflakeServiceError(
                "SNOWFLAKE_DATABASE and SNOWFLAKE_SCHEMA are required for an unqualified stage name."
            )
        return config.snowflake_database, config.snowflake_schema, parts[0]
    raise SnowflakeServiceError(
        "SNOWFLAKE_STAGE_NAME must be STAGE, SCHEMA.STAGE, or DATABASE.SCHEMA.STAGE."
    )


def _connect(config: Settings = settings):
    try:
        import snowflake.connector
    except ImportError as exc:
        raise SnowflakeServiceError(
            "snowflake-connector-python is not installed. Install backend requirements before loading Snowflake."
        ) from exc

    try:
        return snowflake.connector.connect(
            account=config.snowflake_account,
            user=config.snowflake_user,
            password=config.snowflake_password,
            role=config.snowflake_role,
            warehouse=config.snowflake_warehouse,
            database=config.snowflake_database,
            schema=config.snowflake_schema,
        )
    except Exception as exc:
        raise SnowflakeServiceError("Snowflake connection failed.") from exc


def check_connection_and_stage(config: Settings = settings) -> None:
    if not config.snowflake_stage_name:
        raise SnowflakeServiceError("SNOWFLAKE_STAGE_NAME is not configured.")

    connection = _connect(config)
    try:
        cursor = connection.cursor()
        try:
            try:
                cursor.execute("SELECT 1")
            except Exception as exc:
                raise SnowflakeServiceError(
                    "Snowflake connection query failed; verify warehouse, database, schema, and role access."
                ) from exc

            database, schema, stage = _stage_lookup_parts(config.snowflake_stage_name, config)
            schema_ref = _quote_qualified_name(f"{database}.{schema}")
            stage_pattern = stage.replace("'", "''")
            try:
                cursor.execute(f"SHOW STAGES LIKE '{stage_pattern}' IN SCHEMA {schema_ref}")
                stages = cursor.fetchall()
            except Exception as exc:
                raise SnowflakeServiceError(
                    "Snowflake stage lookup failed; verify SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, role access, and stage qualification."
                ) from exc
            if not stages:
                raise SnowflakeServiceError(
                    "Snowflake stage was not found or the configured role lacks access."
                )
            stage_columns = [
                str(column[0]).lower()
                for column in (getattr(cursor, "description", None) or [])
            ]
            stage_url = ""
            if "url" in stage_columns:
                url_index = stage_columns.index("url")
                stage_url = str(stages[0][url_index] or "")
            if not stage_url.lower().startswith("s3://"):
                raise SnowflakeServiceError(
                    "Snowflake stage was found, but it is not an external S3 stage."
                )

            try:
                cursor.execute(f"DESC STAGE {_quote_qualified_name(config.snowflake_stage_name)}")
            except Exception as exc:
                raise SnowflakeServiceError(
                    "Snowflake stage exists, but DESC STAGE failed; verify external stage privileges and stage qualification."
                ) from exc
        finally:
            cursor.close()
    finally:
        connection.close()


def create_and_load_raw_table(
    *,
    dataset_id: str,
    snowflake_columns: list[str],
    storage_key: str,
    config: Settings = settings,
) -> SnowflakeLoadResult:
    if not config.snowflake_stage_name:
        raise SnowflakeServiceError("SNOWFLAKE_STAGE_NAME is not configured.")

    raw_table_name = raw_table_name_for_dataset(dataset_id)
    quoted_table = _quote_identifier(raw_table_name)
    quoted_stage = _quote_qualified_name(config.snowflake_stage_name)
    quoted_columns = [_quote_identifier(column) for column in snowflake_columns]
    columns_sql = ", ".join(f"{column} VARCHAR" for column in quoted_columns)
    escaped_stage_path = storage_key.replace("'", "''")

    connection = _connect(config)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(f"CREATE TABLE {quoted_table} ({columns_sql})")
            cursor.execute(
                f"""
                COPY INTO {quoted_table}
                FROM @{quoted_stage}/{escaped_stage_path}
                FILE_FORMAT = (
                    TYPE = CSV
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                    EMPTY_FIELD_AS_NULL = TRUE
                    NULL_IF = ('', 'NULL', 'null')
                )
                """
            )
            cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
            row = cursor.fetchone()
            rows_loaded = int(row[0] if row else 0)
            if rows_loaded <= 0:
                cursor.execute(f"DROP TABLE IF EXISTS {quoted_table}")
                raise SnowflakeServiceError(
                    "Snowflake raw load completed but loaded zero rows."
                )
        finally:
            cursor.close()
    except SnowflakeServiceError:
        raise
    except Exception as exc:
        raise SnowflakeServiceError("Snowflake raw load failed.") from exc
    finally:
        connection.close()

    return SnowflakeLoadResult(raw_table_name=raw_table_name, rows_loaded=rows_loaded)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def execute_analysis_query(
    *,
    sql: str,
    preview_limit: int = 100,
    config: Settings = settings,
) -> SnowflakeQueryResult:
    if not sql.lstrip().upper().startswith("SELECT"):
        raise SnowflakeServiceError("Only SELECT analysis queries are allowed.")

    connection = _connect(config)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
            description = cursor.description or []
            column_names = [str(column[0]) for column in description]
            output_schema = [
                {
                    "name": str(column[0]),
                    "type": str(column[1]) if len(column) > 1 else "unknown",
                }
                for column in description
            ]
            rows = cursor.fetchmany(preview_limit)
            preview_rows = [
                {
                    column_name: _json_safe(value)
                    for column_name, value in zip(column_names, row, strict=False)
                }
                for row in rows
            ]
        finally:
            cursor.close()
    except Exception as exc:
        raise SnowflakeServiceError("Snowflake analysis query failed.") from exc
    finally:
        connection.close()

    return SnowflakeQueryResult(
        output_schema=output_schema,
        preview_rows=preview_rows,
        row_count=len(preview_rows),
    )


def execute_raw_table_preview(
    *,
    raw_table_name: str,
    columns: list[tuple[str, str]],
    preview_limit: int = 10,
    config: Settings = settings,
) -> SnowflakeQueryResult:
    if not raw_table_name.startswith("RAW_UPLOAD_"):
        raise SnowflakeServiceError("Only MeshFlow-generated raw upload tables can be previewed.")
    if preview_limit < 1 or preview_limit > 50:
        raise SnowflakeServiceError("Raw table preview limit must be between 1 and 50.")
    if not columns:
        return SnowflakeQueryResult(output_schema=[], preview_rows=[], row_count=0)

    quoted_table = _quote_identifier(raw_table_name)
    snowflake_columns = [snowflake_name for snowflake_name, _raw_name in columns]
    raw_columns = [raw_name for _snowflake_name, raw_name in columns]
    selected_columns = ", ".join(_quote_identifier(column) for column in snowflake_columns)

    connection = _connect(config)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(f"SELECT {selected_columns} FROM {quoted_table} LIMIT {int(preview_limit)}")
            rows = cursor.fetchall()
            preview_rows = [
                {
                    raw_column: _json_safe(value)
                    for raw_column, value in zip(raw_columns, row, strict=False)
                }
                for row in rows
            ]
        finally:
            cursor.close()
    except Exception as exc:
        raise SnowflakeServiceError("Snowflake raw table preview query failed.") from exc
    finally:
        connection.close()

    return SnowflakeQueryResult(
        output_schema=[
            {"name": raw_column, "type": "raw"}
            for raw_column in raw_columns
        ],
        preview_rows=preview_rows,
        row_count=len(preview_rows),
    )


def drop_raw_table_for_cleanup(
    *,
    raw_table_name: str | None,
    config: Settings = settings,
) -> CleanupOperationResult:
    if not raw_table_name:
        return CleanupOperationResult(status="skipped")
    if not raw_table_name.startswith("RAW_UPLOAD_"):
        return CleanupOperationResult(
            status="skipped",
            warning=(
                "Snowflake cleanup skipped because the raw table name is not a "
                "MeshFlow-generated RAW_UPLOAD table."
            ),
        )
    if not (
        config.snowflake_account
        and config.snowflake_user
        and config.snowflake_password
        and config.snowflake_warehouse
        and config.snowflake_database
        and config.snowflake_schema
    ):
        return CleanupOperationResult(
            status="not_configured",
            warning="Snowflake cleanup skipped because Snowflake is not fully configured.",
        )

    connection = None
    try:
        connection = _connect(config)
        cursor = connection.cursor()
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {_quote_identifier(raw_table_name)}")
        finally:
            cursor.close()
    except Exception as exc:
        return CleanupOperationResult(
            status="failed",
            warning=(
                f"Snowflake cleanup failed for raw table {raw_table_name}: "
                f"{exc.__class__.__name__}."
            ),
        )
    finally:
        if connection is not None:
            connection.close()

    return CleanupOperationResult(status="completed")


def drop_tables_for_cleanup(
    *,
    table_names: Iterable[str],
    config: Settings = settings,
) -> CleanupOperationResult:
    names = list(dict.fromkeys(table_names))
    if not names:
        return CleanupOperationResult(status="skipped")
    if not (
        config.snowflake_account
        and config.snowflake_user
        and config.snowflake_password
        and config.snowflake_warehouse
        and config.snowflake_database
        and config.snowflake_schema
    ):
        return CleanupOperationResult(
            status="not_configured",
            warning="Snowflake cleanup skipped because Snowflake is not fully configured.",
        )

    connection = None
    try:
        quoted_names = [_quote_identifier(name) for name in names]
        connection = _connect(config)
        cursor = connection.cursor()
        try:
            for quoted_name in quoted_names:
                cursor.execute(f"DROP TABLE IF EXISTS {quoted_name}")
        finally:
            cursor.close()
    except Exception as exc:
        return CleanupOperationResult(
            status="failed",
            warning=(
                "Snowflake cleanup failed for dbt model tables: "
                f"{exc.__class__.__name__}."
            ),
        )
    finally:
        if connection is not None:
            connection.close()

    return CleanupOperationResult(status="completed")
