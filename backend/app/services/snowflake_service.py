from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

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
            cursor.execute("SELECT 1")
            cursor.execute(f"DESC STAGE {_quote_qualified_name(config.snowflake_stage_name)}")
        finally:
            cursor.close()
    except Exception as exc:
        raise SnowflakeServiceError("Snowflake readiness check failed.") from exc
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
        finally:
            cursor.close()
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
