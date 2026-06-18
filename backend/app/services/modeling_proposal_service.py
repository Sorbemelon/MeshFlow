from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Sequence

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.errors import AppError
from app.models.dataset import AiProviderRun, ColumnProfile, Dataset
from app.services.semantic_preparation_service import (
    ProviderCallError,
    ProviderCandidate,
    call_gemini_provider,
    call_openai_provider,
    gemini_key_candidates,
    openai_candidate,
)


TASK_TYPE = "modeling_proposal"
TEMPERATURE = 0.1
MAX_DIMENSIONS = 6
MAX_DIMENSION_COLUMNS = 8
MAX_MARTS = 4
MAX_MART_DIMENSIONS = 3
MAX_MART_METRICS = 4
SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
NUMERIC_DETECTED_TYPES = {"integer", "decimal"}
DATE_DETECTED_TYPES = {"date"}
DIMENSION_ROLES = {"identifier", "dimension", "date_time"}
MEASURE_ROLES = {"measure_column", "metric_candidate"}


class ModelingProposalValidationError(Exception):
    pass


@dataclass(frozen=True)
class ModelingColumn:
    profile: ColumnProfile
    approved_name: str
    approved_role: str


@dataclass(frozen=True)
class ValidatedModelDimension:
    name: str
    key_column: str
    columns: list[str]


@dataclass(frozen=True)
class ValidatedModelMart:
    name: str
    grain: str
    dimensions: list[str]
    metrics: list[str]


@dataclass(frozen=True)
class ValidatedModelingProposal:
    grain: str
    fact_table_name: str
    fact_grain: str
    fact_keys: list[str]
    fact_measures: list[str]
    fact_dimension_keys: list[str]
    fact_degenerate_dimensions: list[str]
    fact_date_columns: list[str]
    dimensions: list[ValidatedModelDimension]
    marts: list[ValidatedModelMart]
    provider_name: str | None = None
    provider_model: str | None = None


def provider_candidates(config: Settings = settings) -> list[ProviderCandidate]:
    return [
        *gemini_key_candidates("gemini_model_1", config.gemini_model_1, config),
        *gemini_key_candidates("gemini_model_2", config.gemini_model_2, config),
        openai_candidate("openai_fallback", config),
    ]


def _as_modeling_columns(mappings: Sequence[Any]) -> list[ModelingColumn]:
    columns: list[ModelingColumn] = []
    for mapping in mappings:
        profile = mapping.profile
        approved_name = str(mapping.approved_name)
        approved_role = str(mapping.approved_role)
        if SAFE_NAME_RE.fullmatch(approved_name):
            columns.append(
                ModelingColumn(
                    profile=profile,
                    approved_name=approved_name,
                    approved_role=approved_role,
                )
            )
    return columns


def _role_groups(columns: list[ModelingColumn]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for column in columns:
        groups.setdefault(column.approved_role, []).append(column.approved_name)
    return groups


def _entity_hints(columns: list[ModelingColumn]) -> dict[str, list[str]]:
    names = [column.approved_name for column in columns]
    name_set = set(names)
    hints: dict[str, list[str]] = {}
    for name in names:
        if not name.endswith("_id"):
            continue
        entity = name.removesuffix("_id")
        entity_columns = [
            candidate
            for candidate in names
            if candidate == name or candidate.startswith(f"{entity}_")
        ]
        if len(entity_columns) > 1:
            hints[entity] = entity_columns

    transaction_attributes = [
        name
        for name in names
        if name
        in {
            "channel",
            "payment_method",
            "payment_terms",
            "order_priority",
            "priority",
            "status",
        }
        or name.endswith("_status")
        or name.endswith("_type")
    ]
    if transaction_attributes:
        hints["transaction_attributes"] = transaction_attributes

    # Keep line/order identifiers visible as grain evidence even when they have no attributes.
    grain_columns = [
        name
        for name in names
        if name in name_set
        and (
            name.endswith("_line_id")
            or name.endswith("_item_id")
            or name in {"order_id", "invoice_id", "transaction_id"}
        )
    ]
    if grain_columns:
        hints["grain_evidence"] = grain_columns
    return hints


def build_modeling_proposal_prompt(
    *,
    dataset: Dataset,
    mappings: Sequence[Any],
) -> str:
    columns = _as_modeling_columns(mappings)
    context = {
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "source_type": dataset.source_type,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
        },
        "columns": [
            {
                "raw_column_name": column.profile.raw_column_name,
                "approved_name": column.approved_name,
                "semantic_role": column.approved_role,
                "detected_type": column.profile.detected_type,
                "null_rate": column.profile.null_rate,
                "unique_count": column.profile.unique_count,
                "sample_values": column.profile.sample_values_json[:5],
            }
            for column in columns
        ],
        "role_groups": _role_groups(columns),
        "entity_hints": _entity_hints(columns),
        "quality_priorities": [
            "Use one fact table at the clearest atomic business grain.",
            "For commercial line-level data, prefer one row per invoice/order line.",
            "Do not create an invoice/order dimension unless it has descriptive attributes beyond ids and dates.",
            "Use dimensions for stable descriptive entities with keys and attributes.",
            "Use degenerate dimensions for low-cardinality transaction attributes such as channel, payment terms, priority, or status.",
            "Prefer the primary business event date for monthly trend marts.",
            "Prefer 3-4 dashboard-useful marts: monthly trend, product/category performance, customer/segment performance, and one operational/geography/supplier mart when justified.",
        ],
        "hard_limits": [
            "Return JSON only. Do not include markdown.",
            "Do not generate SQL. MeshFlow backend generates all dbt SQL.",
            "Use only approved_name values from the provided columns.",
            "Do not invent columns, tables, metrics, dimensions, marts, facts, or analyses.",
            "Prefer one clear fact table and a compact set of dimensions.",
            "Create Data Marts only from columns that exist in the proposed fact, dimensions, date month fields, or degenerate dimensions.",
            "Use needs_review in warnings if the business grain is uncertain.",
            f"Maximum dimensions: {MAX_DIMENSIONS}.",
            f"Maximum marts: {MAX_MARTS}.",
        ],
    }
    schema = {
        "grain": "one row per business event or line item",
        "fact_table": {
            "name": "fact_safe_business_events",
            "grain": "one row per business event or line item",
            "keys": ["safe_identifier_column"],
            "measures": ["safe_numeric_measure"],
            "degenerate_dimensions": ["safe_fact_level_dimension"],
            "date_columns": ["safe_date_column"],
        },
        "dimensions": [
            {
                "name": "dim_safe_entity",
                "key_column": "safe_identifier_column",
                "columns": ["safe_identifier_column", "safe_dimension_attribute"],
            }
        ],
        "marts": [
            {
                "name": "mart_monthly_performance",
                "grain": "one row per month",
                "dimensions": ["safe_date_column_month"],
                "metrics": ["safe_numeric_measure"],
            }
        ],
        "warnings": [],
    }
    return (
        "You are proposing a dimensional model for MeshFlow after semantic column mapping.\n"
        "Return strict JSON only and follow the output schema exactly.\n"
        "Your output is a modeling proposal, not executable code.\n"
        "MeshFlow will validate the proposal and generate backend-owned dbt SQL.\n"
        "Optimize for an analysis-ready star schema and dashboard-friendly Data Marts, "
        "not merely valid table names.\n"
        "Follow these modeling rules in order:\n"
        "1. Pick the clearest atomic business grain.\n"
        "2. Use exactly one fact table unless the context clearly has multiple grains.\n"
        "3. Build dimensions only for descriptive entities with keys and attributes.\n"
        "4. Keep transactional attributes such as channel, payment terms, priority, "
        "and status as fact_table.degenerate_dimensions.\n"
        "5. Do not make invoice/order ids into a separate dimension unless there are "
        "useful invoice/order attributes.\n"
        "6. Prefer 3-4 marts: monthly revenue trend, product/category performance, "
        "customer/segment performance, and one operational/geography/supplier mart if justified.\n"
        "7. Each mart must include dimensions that exist in fact keys, dimension attributes, "
        "date month fields, or degenerate dimensions.\n"
        "8. Include revenue, margin, and quantity measures when present and relevant.\n"
        "9. Add warnings for ambiguity; never invent fields.\n"
        "Use table names beginning with fact_, dim_, and mart_.\n"
        "Monthly groupings may use the pattern <date_column>_month for date columns.\n"
        "Fact-level low-cardinality fields such as channel, priority, or payment terms may "
        "be listed as fact_table.degenerate_dimensions instead of separate dimensions.\n"
        f"Output schema: {json.dumps(schema, separators=(',', ':'))}\n"
        f"Context: {json.dumps(context, separators=(',', ':'))}"
    )


def _safe_text(value: Any, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise ModelingProposalValidationError("Expected a string value.")
    text = re.sub(r"\s+", " ", value.strip())
    if not text or len(text) > max_length:
        raise ModelingProposalValidationError("String value is empty or too long.")
    return text


def _safe_name(value: Any, *, prefix: str | None = None) -> str:
    name = _safe_text(value, max_length=64)
    if not SAFE_NAME_RE.fullmatch(name):
        raise ModelingProposalValidationError(f"{name} is not a safe identifier.")
    if prefix and not name.startswith(prefix):
        raise ModelingProposalValidationError(f"{name} must start with {prefix}.")
    return name


def _string_list(value: Any, *, field_name: str, max_items: int) -> list[str]:
    if not isinstance(value, list):
        raise ModelingProposalValidationError(f"{field_name} must be a list.")
    values: list[str] = []
    seen: set[str] = set()
    for item in value[:max_items]:
        text = _safe_text(item, max_length=64)
        if text in seen:
            continue
        seen.add(text)
        values.append(text)
    return values


def _column_sets(columns: list[ModelingColumn]) -> dict[str, set[str]]:
    all_columns = {column.approved_name for column in columns}
    measures = {
        column.approved_name
        for column in columns
        if column.approved_role in MEASURE_ROLES
        or column.profile.detected_type in NUMERIC_DETECTED_TYPES
    }
    dates = {
        column.approved_name
        for column in columns
        if column.approved_role == "date_time" or column.profile.detected_type in DATE_DETECTED_TYPES
    }
    dimensions = {
        column.approved_name
        for column in columns
        if column.approved_role in DIMENSION_ROLES
        or column.approved_name not in measures
    }
    identifiers = {
        column.approved_name
        for column in columns
        if column.approved_role == "identifier" or column.profile.detected_type == "identifier"
    }
    return {
        "all": all_columns,
        "measures": measures,
        "dates": dates,
        "dimensions": dimensions,
        "identifiers": identifiers,
    }


def _validate_known_columns(values: list[str], known_columns: set[str], field_name: str) -> None:
    unknown = sorted(value for value in values if value not in known_columns)
    if unknown:
        raise ModelingProposalValidationError(
            f"{field_name} referenced unknown columns: {', '.join(unknown)}."
        )


def validate_modeling_proposal_output(
    raw_text: str,
    *,
    mappings: Sequence[Any],
    provider_name: str | None = None,
    provider_model: str | None = None,
) -> ValidatedModelingProposal:
    lowered = raw_text.lower()
    if "api_key" in lowered or "secret" in lowered or "password" in lowered:
        raise ModelingProposalValidationError("Provider output included secret-like text.")
    try:
        body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ModelingProposalValidationError("Provider output was not valid JSON.") from exc
    if not isinstance(body, dict):
        raise ModelingProposalValidationError("Provider output must be a JSON object.")

    columns = _as_modeling_columns(mappings)
    if not columns:
        raise ModelingProposalValidationError("No mapped columns are available.")
    sets = _column_sets(columns)
    grain = _safe_text(body.get("grain"), max_length=180)

    fact_value = body.get("fact_table")
    if not isinstance(fact_value, dict):
        raise ModelingProposalValidationError("fact_table must be an object.")
    fact_table_name = _safe_name(fact_value.get("name"), prefix="fact_")
    fact_grain = _safe_text(fact_value.get("grain", grain), max_length=180)
    fact_keys = _string_list(fact_value.get("keys", []), field_name="fact_table.keys", max_items=6)
    fact_measures = _string_list(
        fact_value.get("measures", []),
        field_name="fact_table.measures",
        max_items=8,
    )
    fact_degenerate_dimensions = _string_list(
        fact_value.get("degenerate_dimensions", []),
        field_name="fact_table.degenerate_dimensions",
        max_items=8,
    )
    fact_date_columns = _string_list(
        fact_value.get("date_columns", []),
        field_name="fact_table.date_columns",
        max_items=4,
    )
    _validate_known_columns(fact_keys, sets["all"], "fact_table.keys")
    _validate_known_columns(fact_measures, sets["all"], "fact_table.measures")
    _validate_known_columns(
        fact_degenerate_dimensions,
        sets["all"],
        "fact_table.degenerate_dimensions",
    )
    _validate_known_columns(fact_date_columns, sets["all"], "fact_table.date_columns")
    if not fact_measures or not set(fact_measures).issubset(sets["measures"]):
        raise ModelingProposalValidationError("fact_table.measures must use mapped numeric measures.")
    if fact_degenerate_dimensions and not set(fact_degenerate_dimensions).issubset(sets["dimensions"]):
        raise ModelingProposalValidationError(
            "fact_table.degenerate_dimensions must use mapped dimension fields."
        )
    if fact_date_columns and not set(fact_date_columns).issubset(sets["dates"]):
        raise ModelingProposalValidationError("fact_table.date_columns must use mapped dates.")

    dimension_values = body.get("dimensions")
    if not isinstance(dimension_values, list) or not dimension_values:
        raise ModelingProposalValidationError("At least one dimension is required.")
    dimensions: list[ValidatedModelDimension] = []
    dimension_names: set[str] = set()
    dimension_attribute_columns: set[str] = set()
    for value in dimension_values[:MAX_DIMENSIONS]:
        if not isinstance(value, dict):
            raise ModelingProposalValidationError("Dimension entries must be objects.")
        name = _safe_name(value.get("name"), prefix="dim_")
        if name in dimension_names:
            raise ModelingProposalValidationError("Dimension names must be unique.")
        dimension_names.add(name)
        key_column = _safe_name(value.get("key_column"))
        columns_value = _string_list(
            value.get("columns"),
            field_name=f"{name}.columns",
            max_items=MAX_DIMENSION_COLUMNS,
        )
        if key_column not in columns_value:
            columns_value.insert(0, key_column)
        _validate_known_columns([key_column, *columns_value], sets["all"], name)
        invalid_attributes = [
            column
            for column in columns_value
            if column in sets["measures"] and column != key_column
        ]
        if invalid_attributes:
            raise ModelingProposalValidationError(
                f"{name} includes measure columns as dimension attributes."
            )
        if key_column not in sets["dimensions"] and key_column not in sets["identifiers"]:
            raise ModelingProposalValidationError(f"{name} key_column is not a mapped dimension key.")
        dimension_attribute_columns.update(columns_value)
        dimensions.append(
            ValidatedModelDimension(name=name, key_column=key_column, columns=columns_value)
        )

    fact_dimension_keys = [dimension.key_column for dimension in dimensions]
    if fact_keys:
        fact_dimension_keys = [*fact_keys, *fact_dimension_keys]
    fact_dimension_keys = list(dict.fromkeys(fact_dimension_keys))

    mart_values = body.get("marts")
    if not isinstance(mart_values, list) or not mart_values:
        raise ModelingProposalValidationError("At least one Data Mart is required.")
    month_columns = {f"{date_column}_month" for date_column in fact_date_columns}
    mart_dimension_candidates = {
        *fact_dimension_keys,
        *fact_degenerate_dimensions,
        *dimension_attribute_columns,
        *fact_date_columns,
        *month_columns,
    }
    marts: list[ValidatedModelMart] = []
    mart_names: set[str] = set()
    inferred_degenerate_dimensions: list[str] = []
    for value in mart_values[:MAX_MARTS]:
        if not isinstance(value, dict):
            raise ModelingProposalValidationError("Mart entries must be objects.")
        name = _safe_name(value.get("name"), prefix="mart_")
        if name in mart_names:
            raise ModelingProposalValidationError("Mart names must be unique.")
        mart_names.add(name)
        mart_grain = _safe_text(value.get("grain", "one row per mart grouping"), max_length=180)
        mart_dimensions = _string_list(
            value.get("dimensions", []),
            field_name=f"{name}.dimensions",
            max_items=MAX_MART_DIMENSIONS,
        )
        mart_metrics = _string_list(
            value.get("metrics", []),
            field_name=f"{name}.metrics",
            max_items=MAX_MART_METRICS,
        )
        if not mart_dimensions:
            raise ModelingProposalValidationError(f"{name} needs at least one dimension.")
        if not mart_metrics:
            raise ModelingProposalValidationError(f"{name} needs at least one metric.")
        unknown_dimensions = []
        for dimension in mart_dimensions:
            if dimension in mart_dimension_candidates:
                continue
            if dimension in sets["dimensions"] and dimension not in sets["measures"]:
                inferred_degenerate_dimensions.append(dimension)
                mart_dimension_candidates.add(dimension)
                continue
            unknown_dimensions.append(dimension)
        unknown_dimensions = sorted(unknown_dimensions)
        if unknown_dimensions:
            raise ModelingProposalValidationError(
                f"{name} referenced dimensions unavailable to generated SQL."
            )
        if not set(mart_metrics).issubset(set(fact_measures)):
            raise ModelingProposalValidationError(f"{name} metrics must use fact measures.")
        marts.append(
            ValidatedModelMart(
                name=name,
                grain=mart_grain,
                dimensions=mart_dimensions,
                metrics=mart_metrics,
            )
        )

    fact_degenerate_dimensions = list(
        dict.fromkeys([*fact_degenerate_dimensions, *inferred_degenerate_dimensions])
    )

    return ValidatedModelingProposal(
        grain=grain,
        fact_table_name=fact_table_name,
        fact_grain=fact_grain,
        fact_keys=fact_keys,
        fact_measures=fact_measures,
        fact_dimension_keys=fact_dimension_keys,
        fact_degenerate_dimensions=fact_degenerate_dimensions,
        fact_date_columns=fact_date_columns,
        dimensions=dimensions,
        marts=marts,
        provider_name=provider_name,
        provider_model=provider_model,
    )


def proposal_to_json(proposal: ValidatedModelingProposal) -> dict[str, object]:
    return {
        "grain": proposal.grain,
        "fact_table": {
            "name": proposal.fact_table_name,
            "grain": proposal.fact_grain,
            "keys": proposal.fact_keys,
            "dimension_keys": proposal.fact_dimension_keys,
            "degenerate_dimensions": proposal.fact_degenerate_dimensions,
            "measures": proposal.fact_measures,
            "date_columns": proposal.fact_date_columns,
        },
        "dimensions": [
            {
                "name": dimension.name,
                "key_column": dimension.key_column,
                "columns": dimension.columns,
            }
            for dimension in proposal.dimensions
        ],
        "marts": [
            {
                "name": mart.name,
                "grain": mart.grain,
                "dimensions": mart.dimensions,
                "metrics": mart.metrics,
            }
            for mart in proposal.marts
        ],
        "provider": {
            "name": proposal.provider_name,
            "model": proposal.provider_model,
        },
    }


def proposal_analysis_catalog(proposal: ValidatedModelingProposal) -> dict[str, dict[str, object]]:
    return {
        mart.name: {
            "grain": mart.grain,
            "dimensions": mart.dimensions,
            "metrics": mart.metrics,
        }
        for mart in proposal.marts
    }


def _call_provider(candidate: ProviderCandidate, prompt: str) -> str:
    if candidate.provider_name == "gemini":
        return call_gemini_provider(candidate, prompt, TEMPERATURE)
    return call_openai_provider(candidate, prompt, TEMPERATURE)


def _provider_run(
    *,
    dataset: Dataset,
    candidate: ProviderCandidate,
    status_value: str,
    fallback_from_provider: str | None,
    error_code: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
) -> AiProviderRun:
    return AiProviderRun(
        dataset=dataset,
        task_type=TASK_TYPE,
        provider_name=candidate.lane_name,
        provider_model=candidate.model,
        status=status_value,
        error_code=error_code,
        error_message=error_message,
        fallback_from_provider=fallback_from_provider,
        latency_ms=latency_ms,
    )


def create_modeling_proposal(
    db: Session,
    dataset: Dataset,
    mappings: Sequence[Any],
    *,
    config: Settings = settings,
) -> ValidatedModelingProposal:
    prompt = build_modeling_proposal_prompt(dataset=dataset, mappings=mappings)
    previous_lane: str | None = None
    latest_error = "MeshFlow could not create a valid dimensional modeling proposal."
    saw_configured_provider = False

    for candidate in provider_candidates(config):
        fallback_from = previous_lane
        previous_lane = candidate.lane_name
        if not candidate.api_key or not candidate.model:
            db.add(
                _provider_run(
                    dataset=dataset,
                    candidate=candidate,
                    status_value="unavailable",
                    fallback_from_provider=fallback_from,
                    error_code="AI_PROVIDER_NOT_CONFIGURED",
                    error_message=f"{candidate.lane_name} is not configured.",
                )
            )
            db.flush()
            continue

        saw_configured_provider = True
        started_at = time.perf_counter()
        try:
            provider_output = _call_provider(candidate, prompt)
            proposal = validate_modeling_proposal_output(
                provider_output,
                mappings=mappings,
                provider_name=candidate.provider_name,
                provider_model=candidate.model,
            )
        except ProviderCallError as exc:
            latest_error = exc.message
            db.add(
                _provider_run(
                    dataset=dataset,
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
        except ModelingProposalValidationError as exc:
            latest_error = str(exc)
            db.add(
                _provider_run(
                    dataset=dataset,
                    candidate=candidate,
                    status_value="failed",
                    fallback_from_provider=fallback_from,
                    error_code="MODELING_PROPOSAL_OUTPUT_INVALID",
                    error_message=str(exc),
                    latency_ms=round((time.perf_counter() - started_at) * 1000),
                )
            )
            db.flush()
            continue

        db.add(
            _provider_run(
                dataset=dataset,
                candidate=candidate,
                status_value="completed",
                fallback_from_provider=fallback_from,
                latency_ms=round((time.perf_counter() - started_at) * 1000),
            )
        )
        db.flush()
        return proposal

    raise AppError(
        error_code="MODELING_PROPOSAL_FAILED",
        failed_step="modeling_proposal",
        message=(
            latest_error
            if saw_configured_provider
            else "No AI provider is configured for uploaded CSV modeling proposals."
        ),
        next_action="Check AI provider configuration or improve semantic mappings, then retry Transform.",
        status_code=status.HTTP_502_BAD_GATEWAY if saw_configured_provider else status.HTTP_400_BAD_REQUEST,
    )
