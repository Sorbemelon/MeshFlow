from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset import AnalysisRun, AnalysisRunChart


SUPPORTED_CHART_TYPES = {"kpi", "line", "bar", "horizontal_bar", "table"}
NUMERIC_TYPE_HINTS = ("number", "numeric", "decimal", "fixed", "float", "double", "real", "int")
TIME_TYPE_HINTS = ("date", "time", "timestamp", "month", "year")
SECRET_MARKERS = ("api_key", "secret", "password", "token")
MAX_CHARTS_PER_ANALYSIS = 3


class ChartSpecError(Exception):
    pass


@dataclass(frozen=True)
class GeneratedChart:
    chart_type: str
    title: str
    description: str | None
    chart_spec: dict[str, Any]
    data: list[dict[str, Any]]
    source_model: str | None
    metric_summary: str | None
    dimension_summary: str | None
    sort_order: int = 0


def _schema_fields(output_schema: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for item in output_schema:
        name = item.get("name")
        if isinstance(name, str) and name:
            fields.append(name)
    return fields


def _field_lookup(output_schema: list[dict[str, Any]]) -> dict[str, str]:
    return {field.lower(): field for field in _schema_fields(output_schema)}


def _schema_item(output_schema: list[dict[str, Any]], field: str) -> dict[str, Any] | None:
    for item in output_schema:
        name = item.get("name")
        if isinstance(name, str) and name.lower() == field.lower():
            return item
    return None


def _is_numeric_value(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return False
        try:
            float(text)
        except ValueError:
            return False
        return True
    return False


def _field_is_numeric(
    field: str,
    output_schema: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> bool:
    item = _schema_item(output_schema, field)
    type_name = str(item.get("type", "") if item else "").lower()
    if any(hint in type_name for hint in NUMERIC_TYPE_HINTS):
        return True
    return any(_is_numeric_value(row.get(field)) for row in rows)


def _field_is_time_like(field: str, output_schema: list[dict[str, Any]]) -> bool:
    item = _schema_item(output_schema, field)
    type_name = str(item.get("type", "") if item else "").lower()
    name = field.lower()
    return any(hint in type_name or hint in name for hint in TIME_TYPE_HINTS)


def _humanize(value: str) -> str:
    words = re.sub(r"[_\s]+", " ", value).strip().split()
    return " ".join(word.capitalize() for word in words) if words else value


def _format_for(field: str) -> str | None:
    lowered = field.lower()
    if any(token in lowered for token in ("revenue", "margin", "cost", "sales", "amount")):
        return "currency"
    if any(token in lowered for token in ("rate", "percent", "ratio")):
        return "percent"
    return None


def _metric_names(analysis_run: AnalysisRun) -> list[str]:
    metrics = analysis_run.metrics_json or []
    names: list[str] = []
    for metric in metrics:
        if isinstance(metric, dict) and isinstance(metric.get("name"), str):
            names.append(metric["name"])
    return names


def _dimension_names(analysis_run: AnalysisRun) -> list[str]:
    return [item for item in (analysis_run.dimensions_json or []) if isinstance(item, str)]


def _actual_field(name: str, lookup: dict[str, str]) -> str | None:
    return lookup.get(name.lower())


def _contains_secret(value: object) -> bool:
    text = json.dumps(value, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _table_chart(analysis_run: AnalysisRun, fields: list[str]) -> GeneratedChart:
    if not fields:
        raise ChartSpecError("No output fields are available for a table chart.")
    chart_spec = {
        "type": "table",
        "title": "Analysis Result",
        "columns": [{"field": field, "label": _humanize(field)} for field in fields],
        "source_model": analysis_run.source_model,
        "grain": analysis_run.grain,
        "tags": ["table"],
    }
    return GeneratedChart(
        chart_type="table",
        title="Analysis Result",
        description="Tabular result from the completed Snowflake analysis query.",
        chart_spec=chart_spec,
        data=analysis_run.preview_rows_json or [],
        source_model=analysis_run.source_model,
        metric_summary=", ".join(_metric_names(analysis_run)) or None,
        dimension_summary=", ".join(_dimension_names(analysis_run)) or None,
    )


def _ranking_requested(analysis_run: AnalysisRun) -> bool:
    text = f"{analysis_run.question} {analysis_run.intent or ''}".lower()
    return any(token in text for token in ("top", "rank", "ranking", "highest", "best", "lowest"))


def build_chart_for_analysis(analysis_run: AnalysisRun) -> GeneratedChart:
    output_schema = analysis_run.output_schema_json or []
    rows = analysis_run.preview_rows_json or []
    fields = _schema_fields(output_schema)
    lookup = _field_lookup(output_schema)
    if not fields:
        raise ChartSpecError("Analysis output schema is empty.")

    metric_field = next(
        (
            actual
            for metric in _metric_names(analysis_run)
            if (actual := _actual_field(metric, lookup))
            and _field_is_numeric(actual, output_schema, rows)
        ),
        None,
    )
    dimension_field = next(
        (
            actual
            for dimension in _dimension_names(analysis_run)
            if (actual := _actual_field(dimension, lookup))
        ),
        None,
    )

    if len(rows) == 1 and metric_field and not dimension_field:
        title = _humanize(metric_field)
        chart_spec = {
            "type": "kpi",
            "title": title,
            "value": {
                "field": metric_field,
                "label": title,
                "format": _format_for(metric_field),
            },
            "source_model": analysis_run.source_model,
            "grain": analysis_run.grain,
            "tags": [metric_field.lower(), "kpi"],
        }
        return GeneratedChart(
            chart_type="kpi",
            title=title,
            description="Single aggregate value from the completed analysis result.",
            chart_spec=chart_spec,
            data=rows,
            source_model=analysis_run.source_model,
            metric_summary=metric_field,
            dimension_summary=None,
        )

    if dimension_field and metric_field:
        metric_label = _humanize(metric_field)
        dimension_label = _humanize(dimension_field)
        if _field_is_time_like(dimension_field, output_schema):
            chart_type = "line"
            title = f"{metric_label} Trend"
            semantic_type = "time"
            tags = ["trend", metric_field.lower()]
        else:
            chart_type = "horizontal_bar" if _ranking_requested(analysis_run) else "bar"
            title = f"{metric_label} by {dimension_label}"
            semantic_type = "category"
            tags = ["breakdown", metric_field.lower()]
        x_axis = {
            "field": dimension_field,
            "label": dimension_label,
            "semantic_type": semantic_type,
        }
        y_axis = {
            "field": metric_field,
            "label": metric_label,
            "format": _format_for(metric_field),
        }
        chart_spec = {
            "type": chart_type,
            "title": title,
            "x": x_axis,
            "y": y_axis,
            "source_model": analysis_run.source_model,
            "grain": analysis_run.grain,
            "tags": tags,
        }
        return GeneratedChart(
            chart_type=chart_type,
            title=title,
            description="Generated from stored Snowflake query output.",
            chart_spec=chart_spec,
            data=rows,
            source_model=analysis_run.source_model,
            metric_summary=metric_field,
            dimension_summary=dimension_field,
        )

    return _table_chart(analysis_run, fields)


def _referenced_fields(chart_spec: dict[str, Any]) -> list[str]:
    chart_type = chart_spec.get("type")
    if chart_type == "kpi":
        value = chart_spec.get("value")
        return [value.get("field")] if isinstance(value, dict) and value.get("field") else []
    if chart_type in {"line", "bar", "horizontal_bar"}:
        fields: list[str] = []
        for key in ("x", "y"):
            item = chart_spec.get(key)
            if isinstance(item, dict) and item.get("field"):
                fields.append(item["field"])
        return fields
    if chart_type == "table":
        columns = chart_spec.get("columns")
        if not isinstance(columns, list):
            return []
        return [
            column["field"]
            for column in columns
            if isinstance(column, dict) and isinstance(column.get("field"), str)
        ]
    return []


def validate_chart_spec(
    chart_spec: dict[str, Any],
    *,
    output_schema: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    source_model: str | None,
) -> None:
    chart_type = chart_spec.get("type")
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ChartSpecError("Chart type is not supported.")
    if "plotly" in json.dumps(chart_spec, default=str).lower():
        raise ChartSpecError("Plotly configs are not supported.")
    if source_model and chart_spec.get("source_model") not in {source_model, None}:
        raise ChartSpecError("Chart references an unknown source model.")
    if _contains_secret(chart_spec) or _contains_secret(rows):
        raise ChartSpecError("Chart output contains secret-like text.")

    field_set = set(_schema_fields(output_schema))
    referenced = _referenced_fields(chart_spec)
    if not referenced:
        raise ChartSpecError("ChartSpec does not reference output fields.")
    if not set(referenced) <= field_set:
        raise ChartSpecError("ChartSpec references fields outside the output schema.")

    if chart_type == "kpi":
        value = chart_spec.get("value")
        field = value.get("field") if isinstance(value, dict) else None
        if not isinstance(field, str) or not _field_is_numeric(field, output_schema, rows):
            raise ChartSpecError("KPI charts require a numeric value field.")
        return

    if chart_type in {"line", "bar", "horizontal_bar"}:
        x_axis = chart_spec.get("x")
        y_axis = chart_spec.get("y")
        x_field = x_axis.get("field") if isinstance(x_axis, dict) else None
        y_field = y_axis.get("field") if isinstance(y_axis, dict) else None
        if not isinstance(x_field, str) or not isinstance(y_field, str):
            raise ChartSpecError("Cartesian charts require x and y fields.")
        if not _field_is_numeric(y_field, output_schema, rows):
            raise ChartSpecError("Cartesian chart y field must be numeric-like.")
        if chart_type == "line" and not _field_is_time_like(x_field, output_schema):
            raise ChartSpecError("Line chart x field must be time-like.")
        if chart_type in {"bar", "horizontal_bar"} and _field_is_numeric(
            x_field,
            output_schema,
            rows,
        ):
            raise ChartSpecError("Bar chart x field must be categorical.")
        return

    columns = chart_spec.get("columns")
    if chart_type == "table" and not isinstance(columns, list):
        raise ChartSpecError("Table charts require columns.")


def chart_summary(chart: AnalysisRunChart) -> dict[str, Any]:
    return {
        "id": chart.id,
        "analysis_run_id": chart.analysis_run_id,
        "dataset_id": chart.dataset_id,
        "chart_type": chart.chart_type,
        "title": chart.title,
        "description": chart.description,
        "chart_spec": chart.chart_spec_json,
        "data": chart.data_json,
        "source_model": chart.source_model,
        "metric_summary": chart.metric_summary,
        "dimension_summary": chart.dimension_summary,
        "sort_order": chart.sort_order,
        "created_at": chart.created_at.isoformat(),
    }


def store_analysis_charts(
    db: Session,
    analysis_run: AnalysisRun,
    *,
    max_charts: int = MAX_CHARTS_PER_ANALYSIS,
) -> list[AnalysisRunChart]:
    if analysis_run.status != "completed":
        raise ChartSpecError("Analysis must be completed before charts can be generated.")
    if max_charts > MAX_CHARTS_PER_ANALYSIS:
        raise ChartSpecError("Chart count exceeds the per-analysis maximum.")
    if analysis_run.charts:
        return list(analysis_run.charts)

    generated = [build_chart_for_analysis(analysis_run)]
    if len(generated) > max_charts:
        raise ChartSpecError("Generated chart count exceeds the per-analysis maximum.")

    charts: list[AnalysisRunChart] = []
    for index, chart in enumerate(generated):
        validate_chart_spec(
            chart.chart_spec,
            output_schema=analysis_run.output_schema_json or [],
            rows=chart.data,
            source_model=analysis_run.source_model,
        )
        model = AnalysisRunChart(
            analysis_run=analysis_run,
            dataset_id=analysis_run.dataset_id,
            chart_type=chart.chart_type,
            title=chart.title,
            description=chart.description,
            chart_spec_json=chart.chart_spec,
            data_json=chart.data,
            source_model=chart.source_model,
            metric_summary=chart.metric_summary,
            dimension_summary=chart.dimension_summary,
            sort_order=index,
        )
        db.add(model)
        charts.append(model)
    db.flush()
    return charts
