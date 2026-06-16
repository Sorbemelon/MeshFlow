from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.core.errors import AppError
from app.models.dataset import AiProviderRun, AnalysisRun, Dataset, DatasetTransformationRun
from app.models.dataset import utc_now as model_utc_now
from app.schemas.analysis import (
    AnalysisRunCreateRequest,
    AnalysisRunDetail,
    AnalysisRunListResponse,
    AnalysisRunResponse,
    AnalysisRunSummary,
)
from app.schemas.dataset import ProviderRunSummary
from app.services import snowflake_service
from app.services.chartspec_service import ChartSpecError, chart_summary, store_analysis_charts
from app.services.dataset_service import RAW_RETAIL_DEMO_SOURCE_TYPE
from app.services.demo_session_service import configured_limits, get_required_session
from app.services.insight_generation_service import (
    ensure_analysis_insights,
    insight_status_for_run,
    insight_summary,
)
from app.services.semantic_preparation_service import (
    ProviderCallError,
    ProviderCandidate,
    call_gemini_provider,
    call_openai_provider,
)


TASK_TYPE = "analysis_plan"
TEMPERATURE = 0.1
MAX_LIMIT = 500
DEFAULT_LIMIT = 100
SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
ALLOWED_AGGREGATIONS = {"sum", "avg", "count", "min", "max"}
ALLOWED_DECISIONS = {"create_new", "needs_user_confirmation"}
RAW_RETAIL_ANALYSIS_CATALOG: dict[str, dict[str, object]] = {
    "mart_sales_performance": {
        "grain": "one row per month",
        "dimensions": ["order_month"],
        "metrics": ["orders", "quantity", "revenue", "gross_margin"],
    },
    "mart_product_performance": {
        "grain": "one row per product category and product",
        "dimensions": ["product_category", "product_name"],
        "metrics": ["quantity", "revenue", "gross_margin"],
    },
    "mart_customer_segments": {
        "grain": "one row per customer segment",
        "dimensions": ["customer_segment"],
        "metrics": ["orders", "revenue", "average_order_value"],
    },
    "mart_store_performance": {
        "grain": "one row per store region and store",
        "dimensions": ["store_region", "store_name"],
        "metrics": ["orders", "revenue"],
    },
}


class AnalysisPlanValidationError(Exception):
    pass


@dataclass(frozen=True)
class AnalysisMetric:
    name: str
    aggregation: str


@dataclass(frozen=True)
class AnalysisFilter:
    field: str
    operator: str
    value: str | int | float | bool | None


@dataclass(frozen=True)
class ValidatedAnalysisPlan:
    decision_type: str
    question: str
    intent: str | None
    source_model: str
    grain: str
    metrics: list[AnalysisMetric]
    dimensions: list[str]
    filters: list[AnalysisFilter]
    sort: list[dict[str, str]]
    limit: int


def normalize_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    return normalized.rstrip(" ?!.")


def provider_candidates(config: Settings = settings) -> list[ProviderCandidate]:
    return [
        ProviderCandidate("openai_primary", "openai", config.openai_api_key, config.openai_model),
        ProviderCandidate("gemini_lane_1", "gemini", config.gemini_api_key_1, config.gemini_model_1),
        ProviderCandidate("gemini_lane_2", "gemini", config.gemini_api_key_2, config.gemini_model_2),
        ProviderCandidate("gemini_lane_3", "gemini", config.gemini_api_key_3, config.gemini_model_3),
    ]


def _provider_summary(run: AiProviderRun) -> ProviderRunSummary:
    return ProviderRunSummary(
        id=run.id,
        task_type=run.task_type,
        provider_name=run.provider_name,
        provider_model=run.provider_model,
        status=run.status,
        error_code=run.error_code,
        error_message=run.error_message,
        fallback_from_provider=run.fallback_from_provider,
        latency_ms=run.latency_ms,
        created_at=run.created_at.isoformat(),
    )


def _analysis_summary(run: AnalysisRun) -> AnalysisRunSummary:
    return AnalysisRunSummary(
        id=run.id,
        demo_session_id=run.demo_session_id,
        dataset_id=run.dataset_id,
        dataset_name=run.dataset.name if run.dataset else None,
        question=run.question,
        normalized_question=run.normalized_question,
        status=run.status,
        decision_type=run.decision_type,
        intent=run.intent,
        source_model=run.source_model,
        grain=run.grain,
        metrics=run.metrics_json or [],
        dimensions=run.dimensions_json or [],
        filters=run.filters_json or [],
        row_count=run.row_count,
        error_code=run.error_code,
        failed_step=run.failed_step,
        error_message=run.error_message,
        chart_count=len(run.charts),
        insight_status=insight_status_for_run(run),
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


def _analysis_detail(
    run: AnalysisRun,
    *,
    decision_type_override: str | None = None,
) -> AnalysisRunDetail:
    summary = _analysis_summary(run).model_dump()
    if decision_type_override:
        summary["decision_type"] = decision_type_override
    return AnalysisRunDetail(
        **summary,
        generated_sql=run.generated_sql,
        output_schema=run.output_schema_json or [],
        preview_rows=run.preview_rows_json or [],
        provider_chain=run.provider_chain_json or [],
        provider_runs=[_provider_summary(provider_run) for provider_run in run.provider_runs],
    )


def _ensure_chart_summaries(
    db: Session,
    run: AnalysisRun,
) -> tuple[list[dict[str, Any]], str, str | None]:
    if run.status != "completed":
        return [], "not_started", None
    if not run.charts:
        try:
            store_analysis_charts(db, run)
        except ChartSpecError as exc:
            return [], "failed", str(exc)
    return [chart_summary(chart) for chart in run.charts], "completed", None


def _analysis_response(
    db: Session,
    run: AnalysisRun,
    *,
    reused: bool,
    decision_type_override: str | None = None,
) -> AnalysisRunResponse:
    charts, chart_status, chart_message = _ensure_chart_summaries(db, run)
    insight_status = "not_started"
    insight_message = None
    if chart_status == "completed" and charts:
        insight_result = ensure_analysis_insights(db, run)
        insight_status = insight_result.status
        insight_message = insight_result.message
    elif run.status == "completed" and chart_status == "failed":
        insight_status = "failed"
        insight_message = "Analysis completed, but chart snapshots are unavailable for insights."
    return AnalysisRunResponse(
        analysis_run=_analysis_detail(run, decision_type_override=decision_type_override),
        charts=charts,
        insights=[insight_summary(insight) for insight in run.insights],
        chart_generation_status=chart_status,
        chart_generation_message=chart_message,
        insight_generation_status=insight_status,
        insight_generation_message=insight_message,
        reused=reused,
    )


def _load_analysis_run_for_session(
    db: Session,
    session_id: str | None,
    analysis_run_id: str,
) -> AnalysisRun:
    session = get_required_session(db, session_id)
    run = db.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.id == analysis_run_id, AnalysisRun.demo_session_id == session.id)
        .options(
            selectinload(AnalysisRun.dataset),
            selectinload(AnalysisRun.provider_runs),
            selectinload(AnalysisRun.charts),
            selectinload(AnalysisRun.insights),
        )
    )
    if run is None:
        raise AppError(
            error_code="ANALYSIS_RUN_NOT_FOUND",
            failed_step="analysis_run",
            message="The requested analysis run was not found for this demo session.",
            next_action="Select an analysis run from this session.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return run


def _attached_dataset_required() -> AppError:
    return AppError(
        error_code="ATTACHED_DATASET_REQUIRED",
        failed_step="attached_dataset",
        message="An explicit attached_dataset_id is required to create an analysis run.",
        next_action="Attach one ready dataset, then retry.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _load_ready_dataset(db: Session, session_id: str, dataset_id: str) -> Dataset:
    dataset = db.scalar(
        select(Dataset)
        .where(
            Dataset.id == dataset_id,
            Dataset.demo_session_id == session_id,
            Dataset.deleted_at.is_(None),
        )
        .options(
            selectinload(Dataset.question_suggestions),
            selectinload(Dataset.semantic_columns),
            selectinload(Dataset.transformation_runs),
            selectinload(Dataset.dbt_artifacts),
        )
    )
    if dataset is None:
        raise AppError(
            error_code="DATASET_NOT_FOUND",
            failed_step="attached_dataset",
            message="The attached dataset was not found for this demo session.",
            next_action="Attach a dataset from the current session.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if dataset.status != "ready_for_analysis":
        raise AppError(
            error_code="DATASET_NOT_READY_FOR_ANALYSIS",
            failed_step="attached_dataset",
            message="The attached dataset is not ready for analysis.",
            next_action="Run dbt transformation successfully before analysis.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return dataset


def _latest_completed_transformation(dataset: Dataset) -> DatasetTransformationRun | None:
    return next(
        (
            run
            for run in reversed(dataset.transformation_runs)
            if run.status == "completed" and run.dbt_run_summary_json
        ),
        None,
    )


def _generic_catalog_from_transformation(dataset: Dataset) -> dict[str, dict[str, object]]:
    latest_run = _latest_completed_transformation(dataset)
    if not latest_run or not latest_run.dbt_run_summary_json:
        return {}
    models = latest_run.dbt_run_summary_json.get("models")
    if not isinstance(models, dict):
        return {}
    data_marts = models.get("data_marts")
    if not isinstance(data_marts, list) or "mart_uploaded_overview" not in data_marts:
        return {}

    return {
        "mart_uploaded_overview": {
            "grain": "one row per uploaded grouping value",
            "dimensions": ["grouping_value"],
            "metrics": ["row_count"],
        }
    }


def analysis_catalog_for_dataset(dataset: Dataset) -> dict[str, dict[str, object]]:
    if dataset.source_type == RAW_RETAIL_DEMO_SOURCE_TYPE:
        return RAW_RETAIL_ANALYSIS_CATALOG
    return _generic_catalog_from_transformation(dataset)


def _catalog_for_or_error(dataset: Dataset) -> dict[str, dict[str, object]]:
    catalog = analysis_catalog_for_dataset(dataset)
    if not catalog:
        raise AppError(
            error_code="UNSUPPORTED_ANALYSIS_DATASET",
            failed_step="analysis_catalog",
            message="This dataset does not have a reliable analysis catalog yet.",
            next_action="Use the Raw Retail Demo or transform an uploaded dataset with supported marts.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return catalog


def _find_reusable_run(
    db: Session,
    *,
    session_id: str,
    dataset_id: str,
    normalized_question: str,
) -> AnalysisRun | None:
    return db.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.demo_session_id == session_id,
            AnalysisRun.dataset_id == dataset_id,
            AnalysisRun.normalized_question == normalized_question,
            AnalysisRun.status == "completed",
        )
        .options(selectinload(AnalysisRun.provider_runs))
        .options(selectinload(AnalysisRun.charts))
        .options(selectinload(AnalysisRun.insights))
        .options(selectinload(AnalysisRun.dataset))
        .order_by(AnalysisRun.completed_at.desc())
    )


def _quota_error() -> AppError:
    return AppError(
        error_code="ANALYSIS_LIMIT_REACHED",
        failed_step="analysis_quota",
        message="This demo session has reached its successful analysis run limit.",
        next_action="Reuse an existing analysis or start a new demo session.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _question_suggestions(dataset: Dataset) -> list[str]:
    return [suggestion.question for suggestion in dataset.question_suggestions[:5]]


def build_analysis_prompt(
    *,
    dataset: Dataset,
    question: str,
    catalog: dict[str, dict[str, object]],
) -> str:
    context = {
        "user_question": question,
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "source_type": dataset.source_type,
            "status": dataset.status,
        },
        "available_marts": catalog,
        "suggested_questions": _question_suggestions(dataset),
        "hard_limits": [
            "Return JSON only.",
            "Do not generate SQL. The backend generates SQL.",
            "Use only available_marts, dimensions, and metrics from context.",
            "Do not claim charts, insights, or dashboard cards are ready.",
            f"Limit must be between 1 and {MAX_LIMIT}.",
        ],
    }
    schema = {
        "decision_type": ["create_new", "needs_user_confirmation"],
        "question": question,
        "intent": "optional_snake_case_intent",
        "source_model": "one available mart name",
        "grain": "grain from context",
        "metrics": [{"name": "allowed metric", "aggregation": "sum"}],
        "dimensions": ["allowed dimension"],
        "filters": [],
        "sort": [{"field": "allowed dimension or metric", "direction": "asc"}],
        "limit": DEFAULT_LIMIT,
        "assumptions": [],
        "warnings": [],
    }
    return (
        "You are planning a MeshFlow analysis run.\n"
        "Return JSON only. Do not include markdown.\n"
        "Do not provide SQL. The backend will generate SQL from your validated plan.\n"
        "Choose exactly one source_model from the available marts.\n"
        "Use only metrics and dimensions listed for that source_model.\n"
        "Use low-risk aggregations: sum, avg, count, min, max.\n"
        "Do not invent columns, marts, insights, ChartSpecs, or dashboard cards.\n"
        f"Output schema: {json.dumps(schema, separators=(',', ':'))}\n"
        f"Context: {json.dumps(context, separators=(',', ':'))}"
    )


def _safe_text(value: Any, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise AnalysisPlanValidationError("Expected a string value.")
    text = value.strip()
    if not text or len(text) > max_length:
        raise AnalysisPlanValidationError("String value is empty or too long.")
    return text


def _optional_safe_text(value: Any, *, max_length: int) -> str | None:
    if value is None:
        return None
    text = _safe_text(value, max_length=max_length)
    if not SAFE_NAME_RE.fullmatch(text):
        raise AnalysisPlanValidationError("Optional name value is not safe.")
    return text


def validate_analysis_plan(
    raw_text: str,
    catalog: dict[str, dict[str, object]],
) -> ValidatedAnalysisPlan:
    lowered = raw_text.lower()
    if "api_key" in lowered or "secret" in lowered:
        raise AnalysisPlanValidationError("Provider output included secret-like text.")
    try:
        body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AnalysisPlanValidationError("Provider output was not valid JSON.") from exc
    if not isinstance(body, dict):
        raise AnalysisPlanValidationError("Provider output must be a JSON object.")
    if "sql" in body or "generated_sql" in body:
        raise AnalysisPlanValidationError("Provider output must not include SQL.")

    decision_type = _safe_text(body.get("decision_type"), max_length=64)
    if decision_type not in ALLOWED_DECISIONS:
        raise AnalysisPlanValidationError("Decision type is not supported.")
    if decision_type != "create_new":
        raise AnalysisPlanValidationError("Provider requested user confirmation.")

    source_model = _safe_text(body.get("source_model"), max_length=128)
    model_catalog = catalog.get(source_model)
    if model_catalog is None:
        raise AnalysisPlanValidationError("Source model is not in the analysis catalog.")
    allowed_metrics = set(model_catalog.get("metrics", []))
    allowed_dimensions = set(model_catalog.get("dimensions", []))

    metric_items = body.get("metrics")
    if not isinstance(metric_items, list) or not metric_items:
        raise AnalysisPlanValidationError("At least one metric is required.")
    metrics: list[AnalysisMetric] = []
    for metric_item in metric_items:
        if not isinstance(metric_item, dict):
            raise AnalysisPlanValidationError("Metric plan item must be an object.")
        name = _safe_text(metric_item.get("name"), max_length=128)
        aggregation = _safe_text(metric_item.get("aggregation"), max_length=32).lower()
        if name not in allowed_metrics:
            raise AnalysisPlanValidationError("Metric is not in the selected model catalog.")
        if aggregation not in ALLOWED_AGGREGATIONS:
            raise AnalysisPlanValidationError("Metric aggregation is not supported.")
        metrics.append(AnalysisMetric(name=name, aggregation=aggregation))

    dimension_items = body.get("dimensions", [])
    if not isinstance(dimension_items, list):
        raise AnalysisPlanValidationError("Dimensions must be a list.")
    dimensions: list[str] = []
    for dimension_item in dimension_items:
        dimension = _safe_text(dimension_item, max_length=128)
        if dimension not in allowed_dimensions:
            raise AnalysisPlanValidationError("Dimension is not in the selected model catalog.")
        if dimension not in dimensions:
            dimensions.append(dimension)

    filter_items = body.get("filters", [])
    if not isinstance(filter_items, list):
        raise AnalysisPlanValidationError("Filters must be a list.")
    filters: list[AnalysisFilter] = []
    for filter_item in filter_items:
        if not isinstance(filter_item, dict):
            raise AnalysisPlanValidationError("Filter item must be an object.")
        field = _safe_text(filter_item.get("field"), max_length=128)
        operator = _safe_text(filter_item.get("operator", "="), max_length=8)
        if field not in allowed_dimensions:
            raise AnalysisPlanValidationError("Filter field must be an allowed dimension.")
        if operator not in {"=", "!="}:
            raise AnalysisPlanValidationError("Filter operator is not supported.")
        value = filter_item.get("value")
        if not isinstance(value, (str, int, float, bool)) and value is not None:
            raise AnalysisPlanValidationError("Filter value is not supported.")
        filters.append(AnalysisFilter(field=field, operator=operator, value=value))

    sort_items = body.get("sort", [])
    if not isinstance(sort_items, list):
        raise AnalysisPlanValidationError("Sort must be a list.")
    sort: list[dict[str, str]] = []
    allowed_sort_fields = allowed_dimensions | allowed_metrics
    for sort_item in sort_items:
        if not isinstance(sort_item, dict):
            raise AnalysisPlanValidationError("Sort item must be an object.")
        field = _safe_text(sort_item.get("field"), max_length=128)
        direction = _safe_text(sort_item.get("direction", "asc"), max_length=8).lower()
        if field not in allowed_sort_fields:
            raise AnalysisPlanValidationError("Sort field is not allowed.")
        if direction not in {"asc", "desc"}:
            raise AnalysisPlanValidationError("Sort direction is not allowed.")
        sort.append({"field": field, "direction": direction})

    limit_value = body.get("limit", DEFAULT_LIMIT)
    if not isinstance(limit_value, int):
        raise AnalysisPlanValidationError("Limit must be an integer.")
    limit = max(1, min(limit_value, MAX_LIMIT))

    return ValidatedAnalysisPlan(
        decision_type=decision_type,
        question=_safe_text(body.get("question"), max_length=500),
        intent=_optional_safe_text(body.get("intent"), max_length=128),
        source_model=source_model,
        grain=_safe_text(body.get("grain", model_catalog.get("grain")), max_length=255),
        metrics=metrics,
        dimensions=dimensions,
        filters=filters,
        sort=sort,
        limit=limit,
    )


def _call_provider(candidate: ProviderCandidate, prompt: str) -> str:
    if candidate.provider_name == "openai":
        return call_openai_provider(candidate, prompt, TEMPERATURE)
    return call_gemini_provider(candidate, prompt, TEMPERATURE)


def _provider_run(
    *,
    dataset: Dataset,
    analysis_run: AnalysisRun,
    candidate: ProviderCandidate,
    status_value: str,
    fallback_from_provider: str | None,
    error_code: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
) -> AiProviderRun:
    return AiProviderRun(
        dataset=dataset,
        analysis_run=analysis_run,
        task_type=TASK_TYPE,
        provider_name=candidate.lane_name,
        provider_model=candidate.model,
        status=status_value,
        error_code=error_code,
        error_message=error_message,
        fallback_from_provider=fallback_from_provider,
        latency_ms=latency_ms,
    )


def _provider_chain(dataset: Dataset, analysis_run: AnalysisRun) -> list[dict[str, object]]:
    return [
        {
            "provider_name": run.provider_name,
            "provider_model": run.provider_model,
            "status": run.status,
            "error_code": run.error_code,
            "fallback_from_provider": run.fallback_from_provider,
        }
        for run in analysis_run.provider_runs
        if run.dataset_id == dataset.id and run.task_type == TASK_TYPE
    ]


def create_analysis_plan(
    *,
    db: Session,
    dataset: Dataset,
    analysis_run: AnalysisRun,
    question: str,
    catalog: dict[str, dict[str, object]],
    config: Settings,
) -> ValidatedAnalysisPlan:
    prompt = build_analysis_prompt(dataset=dataset, question=question, catalog=catalog)
    previous_lane: str | None = None
    for candidate in provider_candidates(config):
        fallback_from = previous_lane
        previous_lane = candidate.lane_name
        if not candidate.api_key or not candidate.model:
            db.add(
                _provider_run(
                    dataset=dataset,
                    analysis_run=analysis_run,
                    candidate=candidate,
                    status_value="unavailable",
                    fallback_from_provider=fallback_from,
                    error_code="AI_PROVIDER_NOT_CONFIGURED",
                    error_message=f"{candidate.lane_name} is not configured.",
                )
            )
            db.flush()
            continue

        started_at = time.perf_counter()
        try:
            provider_output = _call_provider(candidate, prompt)
            plan = validate_analysis_plan(provider_output, catalog)
        except ProviderCallError as exc:
            db.add(
                _provider_run(
                    dataset=dataset,
                    analysis_run=analysis_run,
                    candidate=candidate,
                    status_value="failed",
                    fallback_from_provider=fallback_from,
                    error_code=exc.error_code,
                    error_message=exc.message,
                    latency_ms=round((time.perf_counter() - started_at) * 1000),
                )
            )
            db.flush()
            continue
        except AnalysisPlanValidationError as exc:
            db.add(
                _provider_run(
                    dataset=dataset,
                    analysis_run=analysis_run,
                    candidate=candidate,
                    status_value="failed",
                    fallback_from_provider=fallback_from,
                    error_code="ANALYSIS_PLAN_INVALID",
                    error_message=str(exc),
                    latency_ms=round((time.perf_counter() - started_at) * 1000),
                )
            )
            db.flush()
            continue

        db.add(
            _provider_run(
                dataset=dataset,
                analysis_run=analysis_run,
                candidate=candidate,
                status_value="completed",
                fallback_from_provider=fallback_from,
                latency_ms=round((time.perf_counter() - started_at) * 1000),
            )
        )
        db.flush()
        return plan

    raise AnalysisPlanValidationError(
        "MeshFlow could not create a valid analysis plan using OpenAI or Gemini."
    )


def _model_relation(source_model: str, config: Settings) -> str:
    if config.snowflake_database and config.snowflake_schema:
        return ".".join(
            [
                snowflake_service.quote_identifier(config.snowflake_database),
                snowflake_service.quote_identifier(config.snowflake_schema),
                snowflake_service.quote_identifier(source_model),
            ]
        )
    return snowflake_service.quote_identifier(source_model)


def _literal(value: str | int | float | bool | None) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + value.replace("'", "''") + "'"


def generate_analysis_sql(plan: ValidatedAnalysisPlan, config: Settings = settings) -> str:
    select_parts: list[str] = [
        snowflake_service.quote_identifier(dimension) for dimension in plan.dimensions
    ]
    for metric in plan.metrics:
        metric_identifier = snowflake_service.quote_identifier(metric.name)
        metric_alias = snowflake_service.quote_identifier(metric.name)
        if metric.aggregation == "count":
            select_parts.append(f"COUNT({metric_identifier}) AS {metric_alias}")
        else:
            select_parts.append(
                f"{metric.aggregation.upper()}({metric_identifier}) AS {metric_alias}"
            )

    sql_parts = [
        "SELECT",
        "  " + ",\n  ".join(select_parts),
        f"FROM {_model_relation(plan.source_model, config)}",
    ]
    if plan.filters:
        where_parts = [
            f"{snowflake_service.quote_identifier(filter_item.field)} "
            f"{filter_item.operator} {_literal(filter_item.value)}"
            for filter_item in plan.filters
        ]
        sql_parts.append("WHERE " + " AND ".join(where_parts))
    if plan.dimensions:
        group_parts = [
            snowflake_service.quote_identifier(dimension) for dimension in plan.dimensions
        ]
        sql_parts.append("GROUP BY " + ", ".join(group_parts))
    if plan.sort:
        order_parts = [
            f"{snowflake_service.quote_identifier(item['field'])} {item['direction'].upper()}"
            for item in plan.sort
        ]
        sql_parts.append("ORDER BY " + ", ".join(order_parts))
    sql_parts.append(f"LIMIT {plan.limit}")
    return "\n".join(sql_parts)


def _mark_failed(
    db: Session,
    analysis_run: AnalysisRun,
    *,
    error_code: str,
    failed_step: str,
    error_message: str,
) -> None:
    analysis_run.status = "failed"
    analysis_run.error_code = error_code
    analysis_run.failed_step = failed_step
    analysis_run.error_message = error_message
    analysis_run.provider_chain_json = [
        {
            "provider_name": run.provider_name,
            "status": run.status,
            "error_code": run.error_code,
            "fallback_from_provider": run.fallback_from_provider,
        }
        for run in analysis_run.provider_runs
    ]
    db.commit()


def create_analysis_run(
    db: Session,
    session_id: str | None,
    request: AnalysisRunCreateRequest,
    config: Settings = settings,
) -> AnalysisRunResponse:
    session = get_required_session(db, session_id)
    if not request.attached_dataset_id:
        raise _attached_dataset_required()
    question = request.question.strip()
    normalized_question = normalize_question(question)
    dataset = _load_ready_dataset(db, session.id, request.attached_dataset_id)
    catalog = _catalog_for_or_error(dataset)

    if not request.force_new:
        reusable = _find_reusable_run(
            db,
            session_id=session.id,
            dataset_id=dataset.id,
            normalized_question=normalized_question,
        )
        if reusable is not None:
            response = _analysis_response(
                db,
                reusable,
                reused=True,
                decision_type_override="reuse_existing",
            )
            db.commit()
            return response

    limits = configured_limits(config)
    if session.successful_analysis_runs_used >= limits.max_successful_analysis_runs_per_session:
        raise _quota_error()

    analysis_run = AnalysisRun(
        demo_session_id=session.id,
        dataset=dataset,
        question=question,
        normalized_question=normalized_question,
        status="planning",
        decision_type="create_new",
    )
    db.add(analysis_run)
    db.commit()
    db.refresh(analysis_run)

    try:
        plan = create_analysis_plan(
            db=db,
            dataset=dataset,
            analysis_run=analysis_run,
            question=question,
            catalog=catalog,
            config=config,
        )
    except AnalysisPlanValidationError as exc:
        _mark_failed(
            db,
            analysis_run,
            error_code="ANALYSIS_PLAN_FAILED",
            failed_step="analysis_plan",
            error_message=str(exc),
        )
        raise AppError(
            error_code="ANALYSIS_PLAN_FAILED",
            failed_step="analysis_plan",
            message="MeshFlow could not create a valid analysis plan using OpenAI or Gemini.",
            next_action="Try a supported question or check AI provider configuration.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    analysis_run.status = "validating"
    analysis_run.intent = plan.intent
    analysis_run.source_model = plan.source_model
    analysis_run.grain = plan.grain
    analysis_run.metrics_json = [
        {"name": metric.name, "aggregation": metric.aggregation} for metric in plan.metrics
    ]
    analysis_run.dimensions_json = plan.dimensions
    analysis_run.filters_json = [
        {"field": filter_item.field, "operator": filter_item.operator, "value": filter_item.value}
        for filter_item in plan.filters
    ]
    analysis_run.provider_chain_json = _provider_chain(dataset, analysis_run)
    generated_sql = generate_analysis_sql(plan, config)
    analysis_run.generated_sql = generated_sql
    analysis_run.status = "running"
    db.commit()

    try:
        query_result = snowflake_service.execute_analysis_query(
            sql=generated_sql,
            preview_limit=plan.limit,
            config=config,
        )
    except snowflake_service.SnowflakeServiceError as exc:
        _mark_failed(
            db,
            analysis_run,
            error_code="ANALYSIS_QUERY_FAILED",
            failed_step="snowflake_analysis_query",
            error_message="MeshFlow could not execute the generated Snowflake analysis query.",
        )
        raise AppError(
            error_code="ANALYSIS_QUERY_FAILED",
            failed_step="snowflake_analysis_query",
            message="MeshFlow could not execute the generated Snowflake analysis query.",
            next_action="Check Snowflake readiness, mart availability, and query permissions.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    analysis_run.output_schema_json = query_result.output_schema
    analysis_run.preview_rows_json = query_result.preview_rows
    analysis_run.row_count = query_result.row_count
    analysis_run.status = "completed"
    analysis_run.completed_at = model_utc_now()
    session.successful_analysis_runs_used += 1
    response = _analysis_response(db, analysis_run, reused=False)
    db.commit()
    db.refresh(analysis_run)
    return response


def list_analysis_runs(
    db: Session,
    session_id: str | None,
    dataset_id: str | None = None,
) -> AnalysisRunListResponse:
    session = get_required_session(db, session_id)
    statement = select(AnalysisRun).where(AnalysisRun.demo_session_id == session.id)
    if dataset_id:
        statement = statement.where(AnalysisRun.dataset_id == dataset_id)
    runs = db.scalars(
        statement.options(
            selectinload(AnalysisRun.dataset),
            selectinload(AnalysisRun.charts),
            selectinload(AnalysisRun.insights),
        ).order_by(AnalysisRun.created_at.desc())
    ).all()
    return AnalysisRunListResponse(analysis_runs=[_analysis_summary(run) for run in runs])


def get_analysis_run_detail(
    db: Session,
    session_id: str | None,
    analysis_run_id: str,
) -> AnalysisRunResponse:
    run = _load_analysis_run_for_session(db, session_id, analysis_run_id)
    response = _analysis_response(db, run, reused=False)
    db.commit()
    return response
