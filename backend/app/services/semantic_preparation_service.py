from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, settings
from app.db.session import SessionLocal
from app.core.errors import AppError
from app.models.dataset import (
    AiProviderRun,
    ColumnProfile,
    Dataset,
    SemanticColumn,
)
from app.schemas.dataset import (
    ProviderRunSummary,
    SemanticColumnMappingPatchRequest,
    SemanticColumnSummary,
    SemanticPreparationResponse,
)
from app.services.demo_session_service import get_required_session


TASK_TYPE = "semantic_preparation"
JOB_PROVIDER_NAME = "semantic_preparation_job"
TEMPERATURE = 0.1
SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
ALLOWED_SEMANTIC_ROLES = {
    "identifier",
    "date_time",
    "measure_column",
    "metric_candidate",
    "dimension",
    "unknown",
}


class ProviderCallError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class SemanticOutputValidationError(Exception):
    pass


@dataclass
class ProviderCandidate:
    lane_name: str
    provider_name: str
    api_key: str | None
    model: str | None


def gemini_key_candidates(
    lane_prefix: str,
    model: str | None,
    config: Settings = settings,
) -> list[ProviderCandidate]:
    return [
        ProviderCandidate(f"{lane_prefix}_key_1", "gemini", config.gemini_api_key_1, model),
        ProviderCandidate(f"{lane_prefix}_key_2", "gemini", config.gemini_api_key_2, model),
    ]


def openai_candidate(lane_name: str, config: Settings = settings) -> ProviderCandidate:
    return ProviderCandidate(lane_name, "openai", config.openai_api_key, config.openai_model)


@dataclass
class ValidatedColumnSuggestion:
    column_profile: ColumnProfile
    suggested_name: str
    semantic_role: str
    confidence: float
    needs_review: bool
    reason: str


@dataclass
class ValidatedSemanticOutput:
    columns: list[ValidatedColumnSuggestion]


def provider_candidates(config: Settings = settings) -> list[ProviderCandidate]:
    return [
        *gemini_key_candidates("gemini_model_1", config.gemini_model_1, config),
        openai_candidate("openai_fallback", config),
        *gemini_key_candidates("gemini_model_2", config.gemini_model_2, config),
    ]


def _semantic_column_summary(column: SemanticColumn) -> SemanticColumnSummary:
    return SemanticColumnSummary(
        id=column.id,
        column_profile_id=column.column_profile_id,
        raw_column_name=column.raw_column_name,
        suggested_name=column.suggested_name,
        semantic_role=column.semantic_role,
        confidence=column.confidence,
        needs_review=column.needs_review,
        reason=column.reason,
        approved_name=column.approved_name,
        approved_role=column.approved_role,
        include_in_model=column.include_in_model,
        user_edited=column.user_edited,
        provider_name=column.provider_name,
        provider_model=column.provider_model,
    )


def _provider_run_summary(run: AiProviderRun) -> ProviderRunSummary:
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


def semantic_preparation_summary_from_dataset(
    dataset: Dataset,
    *,
    prefer_latest_failure: bool = False,
) -> SemanticPreparationResponse:
    task_runs = sorted(
        [run for run in dataset.provider_runs if run.task_type == TASK_TYPE],
        key=lambda run: run.created_at,
    )
    semantic_columns = list(dataset.semantic_columns)

    latest_run = task_runs[-1] if task_runs else None
    running_run = next(
        (
            run
            for run in reversed(task_runs)
            if run.provider_name == JOB_PROVIDER_NAME and run.status == "running"
        ),
        None,
    )
    if running_run and not semantic_columns:
        response_status = "running"
        message = "Semantic preparation is running. MeshFlow is checking configured AI providers."
        next_action = "Wait for the semantic preparation status to update."
    elif prefer_latest_failure and latest_run and latest_run.status in {"failed", "unavailable"}:
        response_status = "failed"
        message = (
            latest_run.error_message
            or "AI semantic preparation failed. No fake suggestions were stored."
        )
        next_action = "Configure an AI provider or retry semantic preparation later."
    elif semantic_columns:
        response_status = "completed"
        message = "Semantic suggestions are ready for review."
        next_action = None
    elif task_runs:
        response_status = "failed"
        failed_run = task_runs[-1]
        message = (
            failed_run.error_message
            or "AI semantic preparation failed. No fake suggestions were stored."
        )
        next_action = "Configure an AI provider or retry semantic preparation later."
    else:
        response_status = "not_started"
        message = "Semantic suggestions have not been generated for this dataset."
        next_action = "Generate AI suggestions after reviewing the raw schema profile."

    return SemanticPreparationResponse(
        status=response_status,
        message=message,
        semantic_columns=[_semantic_column_summary(column) for column in semantic_columns],
        provider_runs=[_provider_run_summary(run) for run in task_runs],
        next_action=next_action,
        job_id=running_run.id if running_run else None,
    )


def _load_dataset_for_session(
    db: Session,
    session_id: str | None,
    dataset_id: str,
) -> Dataset:
    session = get_required_session(db, session_id)
    dataset = db.scalar(
        select(Dataset)
        .where(
            Dataset.id == dataset_id,
            Dataset.demo_session_id == session.id,
        )
        .options(
            selectinload(Dataset.column_profiles),
            selectinload(Dataset.semantic_columns),
            selectinload(Dataset.provider_runs),
        )
    )
    if dataset is None:
        raise AppError(
            error_code="DATASET_NOT_FOUND",
            failed_step="dataset",
            message="The requested dataset was not found for this demo session.",
            next_action="Select an available dataset from the workspace.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if dataset.deleted_at is not None or dataset.status == "deleted":
        raise AppError(
            error_code="DATASET_DELETED",
            failed_step="dataset_validation",
            message=(
                "This dataset was deleted from the active workspace. Existing dashboard "
                "cards and history remain available, but semantic preparation cannot run from it."
            ),
            next_action="Upload or prepare another dataset.",
            status_code=status.HTTP_410_GONE,
        )

    return dataset


def _ensure_dataset_has_profiles(dataset: Dataset) -> None:
    if not dataset.column_profiles:
        raise AppError(
            error_code="DATASET_NOT_READY_FOR_SEMANTIC_PREP",
            failed_step="semantic_preparation",
            message="This dataset has no schema profile to send for semantic preparation.",
            next_action="Upload and load a CSV into Warehouse Raw before generating suggestions.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def _profile_context(profile: ColumnProfile) -> dict[str, object]:
    return {
        "column_profile_id": profile.id,
        "raw_column_name": profile.raw_column_name,
        "snowflake_column_name": profile.snowflake_column_name,
        "detected_physical_type": profile.detected_type,
        "null_rate": profile.null_rate,
        "unique_count": profile.unique_count,
        "sample_values": profile.sample_values_json[:5],
    }


def build_semantic_prompt(dataset: Dataset) -> str:
    role_hints = {
        "identifier": [
            "stable keys and id columns such as customer_id, product_id, order_id, invoice_line_id",
        ],
        "date_time": ["business event dates such as order_date, invoice_date, ship_date"],
        "measure_column": [
            "numeric additive values such as revenue, cost, quantity, discount_amount, gross_margin",
        ],
        "metric_candidate": [
            "numeric fields that may become metrics but need review before modeling",
        ],
        "dimension": [
            "descriptive attributes such as customer_segment, product_category, region, channel",
        ],
        "unknown": ["ambiguous columns whose business meaning is not clear from the profile"],
    }
    context = {
        "dataset": {
            "name": dataset.name,
            "source_type": dataset.source_type,
            "status": dataset.status,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
        },
        "role_hints": role_hints,
        "quality_priorities": [
            "Prefer stable physical meaning over guessing business semantics.",
            "Use identifier for id/key columns even if sample values look numeric.",
            "Use date_time for parsed dates or date-like business event fields.",
            "Use measure_column for additive numeric fields used in facts and marts.",
            "Use dimension for categorical descriptors and labels.",
            "Use unknown with needs_review=true when a column cannot be classified honestly.",
        ],
        "known_limits": [
            "Only Warehouse Raw and deterministic schema profiling are available to this task.",
            "This task only maps columns. It must not suggest analysis questions.",
            "Do not invent columns, business facts, or provider evidence.",
        ],
        "columns": [_profile_context(profile) for profile in dataset.column_profiles],
    }
    schema = {
        "columns": [
            {
                "raw_column_name": "existing column name only",
                "suggested_name": "safe_snake_case_name",
                "semantic_role": "exactly one allowed role string",
                "confidence": "number between 0 and 1",
                "needs_review": "boolean",
                "reason": "short reason",
            }
        ],
        "warnings": [],
    }
    return (
        "You are preparing semantic schema suggestions for MeshFlow.\n"
        "Return JSON only. Do not include markdown.\n"
        "Classify every provided column exactly once.\n"
        "Use needs_review=true when business meaning is uncertain, confidence is low, "
        "or semantic_role is unknown.\n"
        "Set confidence lower when a sample value alone is not enough to prove meaning.\n"
        "Keep suggested_name conservative: normalized snake_case of the actual column meaning.\n"
        "For every column object, semantic_role must be exactly one string value from "
        "the allowed semantic roles, not an array or object.\n"
        "suggested_name, raw_column_name, and reason must be strings.\n"
        "Do not invent columns. Every raw_column_name must match the provided context.\n"
        "Do not claim transformations, Data Marts, analysis, charts, or dashboards are ready.\n"
        "Do not return suggested_questions. Suggested analysis questions are generated later "
        "after dbt Data Marts exist.\n"
        f"Allowed semantic roles: {', '.join(sorted(ALLOWED_SEMANTIC_ROLES))}.\n"
        f"Output schema: {json.dumps(schema, separators=(',', ':'))}\n"
        f"Context: {json.dumps(context, separators=(',', ':'))}"
    )


def call_gemini_provider(
    candidate: ProviderCandidate,
    prompt: str,
    temperature: float = TEMPERATURE,
) -> str:
    if not candidate.api_key or not candidate.model:
        raise ProviderCallError("AI_PROVIDER_NOT_CONFIGURED", "Gemini lane is not configured.")

    model = urllib.parse.quote(candidate.model, safe="")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={urllib.parse.quote(candidate.api_key, safe='')}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "Gemini request failed.") from exc

    try:
        return parsed["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderCallError(
            "AI_PROVIDER_OUTPUT_INVALID",
            "Gemini returned an unexpected response shape.",
        ) from exc


def call_openai_provider(
    candidate: ProviderCandidate,
    prompt: str,
    temperature: float = TEMPERATURE,
) -> str:
    if not candidate.api_key or not candidate.model:
        raise ProviderCallError("AI_PROVIDER_NOT_CONFIGURED", "OpenAI fallback is not configured.")

    payload = {
        "model": candidate.model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Return strict JSON only for MeshFlow semantic preparation.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {candidate.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ProviderCallError("AI_PROVIDER_REQUEST_FAILED", "OpenAI request failed.") from exc

    try:
        return parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderCallError(
            "AI_PROVIDER_OUTPUT_INVALID",
            "OpenAI returned an unexpected response shape.",
        ) from exc


def _call_provider(candidate: ProviderCandidate, prompt: str) -> str:
    if candidate.provider_name == "gemini":
        return call_gemini_provider(candidate, prompt, TEMPERATURE)
    return call_openai_provider(candidate, prompt, TEMPERATURE)


def _safe_text(value: Any, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise SemanticOutputValidationError("Expected string value.")
    text = value.strip()
    if not text or len(text) > max_length:
        raise SemanticOutputValidationError("String value is empty or too long.")
    return text


def validate_provider_output(raw_text: str, profiles: list[ColumnProfile]) -> ValidatedSemanticOutput:
    lowered = raw_text.lower()
    if "api_key" in lowered or "secret" in lowered:
        raise SemanticOutputValidationError("Provider output included secret-like text.")

    try:
        body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise SemanticOutputValidationError("Provider output was not valid JSON.") from exc

    if not isinstance(body, dict):
        raise SemanticOutputValidationError("Provider output must be a JSON object.")

    columns_value = body.get("columns")
    if not isinstance(columns_value, list) or not columns_value:
        raise SemanticOutputValidationError("Provider output must include suggested columns.")

    profiles_by_raw_name = {profile.raw_column_name: profile for profile in profiles}
    suggestions: list[ValidatedColumnSuggestion] = []
    seen_raw_names: set[str] = set()
    for item in columns_value:
        if not isinstance(item, dict):
            raise SemanticOutputValidationError("Column suggestion must be an object.")
        raw_column_name = _safe_text(item.get("raw_column_name"), max_length=255)
        profile = profiles_by_raw_name.get(raw_column_name)
        if profile is None or raw_column_name in seen_raw_names:
            raise SemanticOutputValidationError("Column suggestion does not match a unique profile.")
        seen_raw_names.add(raw_column_name)

        suggested_name = _safe_text(item.get("suggested_name"), max_length=64)
        if not SAFE_NAME_RE.fullmatch(suggested_name):
            raise SemanticOutputValidationError("Suggested name is not safe.")
        semantic_role = _safe_text(item.get("semantic_role"), max_length=32)
        if semantic_role not in ALLOWED_SEMANTIC_ROLES:
            raise SemanticOutputValidationError("Semantic role is not allowed.")
        confidence_value = item.get("confidence")
        if not isinstance(confidence_value, int | float):
            raise SemanticOutputValidationError("Confidence must be numeric.")
        confidence = float(confidence_value)
        if confidence < 0 or confidence > 1:
            raise SemanticOutputValidationError("Confidence must be between 0 and 1.")
        needs_review = bool(item.get("needs_review", False))
        if confidence < 0.75 or semantic_role == "unknown":
            needs_review = True
        reason = _safe_text(item.get("reason"), max_length=512)
        suggestions.append(
            ValidatedColumnSuggestion(
                column_profile=profile,
                suggested_name=suggested_name,
                semantic_role=semantic_role,
                confidence=round(confidence, 4),
                needs_review=needs_review,
                reason=reason,
            )
        )

    return ValidatedSemanticOutput(columns=suggestions)


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


def _clear_existing_semantic_columns(db: Session, dataset: Dataset) -> None:
    for semantic_column in list(dataset.semantic_columns):
        db.delete(semantic_column)


def _latest_running_job(dataset: Dataset) -> AiProviderRun | None:
    task_runs = sorted(
        [run for run in dataset.provider_runs if run.task_type == TASK_TYPE],
        key=lambda run: run.created_at,
    )
    return next(
        (
            run
            for run in reversed(task_runs)
            if run.provider_name == JOB_PROVIDER_NAME and run.status == "running"
        ),
        None,
    )


def _finalize_job_run(
    db: Session,
    job_run_id: str | None,
    *,
    status_value: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    if job_run_id is None:
        return
    job_run = db.get(AiProviderRun, job_run_id)
    if job_run is None:
        return
    job_run.status = status_value
    job_run.error_code = error_code
    job_run.error_message = error_message


def _run_semantic_preparation_background(
    *,
    session_id: str,
    dataset_id: str,
    force: bool,
    job_run_id: str,
    config: Settings,
) -> None:
    with SessionLocal() as db:
        try:
            run_semantic_preparation(
                db,
                session_id,
                dataset_id,
                force=force,
                config=config,
                job_run_id=job_run_id,
            )
        except Exception as exc:  # pragma: no cover - defensive job finalizer
            _finalize_job_run(
                db,
                job_run_id,
                status_value="failed",
                error_code="SEMANTIC_PREPARATION_JOB_FAILED",
                error_message="Semantic preparation job failed before storing suggestions.",
            )
            db.commit()


def start_semantic_preparation(
    db: Session,
    session_id: str | None,
    dataset_id: str,
    *,
    force: bool = False,
    config: Settings = settings,
) -> SemanticPreparationResponse:
    session = get_required_session(db, session_id)
    dataset = _load_dataset_for_session(db, session.id, dataset_id)
    _ensure_dataset_has_profiles(dataset)

    if dataset.semantic_columns and not force:
        return semantic_preparation_summary_from_dataset(dataset)

    running_job = _latest_running_job(dataset)
    if running_job is not None:
        return semantic_preparation_summary_from_dataset(dataset)

    job_run = AiProviderRun(
        dataset=dataset,
        task_type=TASK_TYPE,
        provider_name=JOB_PROVIDER_NAME,
        provider_model=None,
        status="running",
        error_message="Semantic preparation is running.",
    )
    db.add(job_run)
    db.commit()
    db.refresh(dataset)
    db.refresh(job_run)

    thread = threading.Thread(
        target=_run_semantic_preparation_background,
        kwargs={
            "session_id": session.id,
            "dataset_id": dataset.id,
            "force": force,
            "job_run_id": job_run.id,
            "config": config,
        },
        daemon=True,
    )
    thread.start()

    return get_semantic_preparation(db, session.id, dataset.id)


def _store_validated_output(
    *,
    db: Session,
    dataset: Dataset,
    output: ValidatedSemanticOutput,
    provider: ProviderCandidate,
) -> None:
    for suggestion in output.columns:
        db.add(
            SemanticColumn(
                dataset=dataset,
                column_profile=suggestion.column_profile,
                raw_column_name=suggestion.column_profile.raw_column_name,
                suggested_name=suggestion.suggested_name,
                semantic_role=suggestion.semantic_role,
                confidence=suggestion.confidence,
                needs_review=suggestion.needs_review,
                reason=suggestion.reason,
                include_in_model=True,
                provider_name=provider.provider_name,
                provider_model=provider.model,
            )
        )


def get_semantic_preparation(
    db: Session,
    session_id: str | None,
    dataset_id: str,
) -> SemanticPreparationResponse:
    dataset = _load_dataset_for_session(db, session_id, dataset_id)
    return semantic_preparation_summary_from_dataset(dataset)


def run_semantic_preparation(
    db: Session,
    session_id: str | None,
    dataset_id: str,
    *,
    force: bool = False,
    config: Settings = settings,
    job_run_id: str | None = None,
) -> SemanticPreparationResponse:
    dataset = _load_dataset_for_session(db, session_id, dataset_id)
    _ensure_dataset_has_profiles(dataset)

    if dataset.semantic_columns and not force:
        return semantic_preparation_summary_from_dataset(dataset)

    prompt = build_semantic_prompt(dataset)
    previous_lane: str | None = None
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
            continue

        started_at = time.perf_counter()
        try:
            provider_output = _call_provider(candidate, prompt)
            validated = validate_provider_output(provider_output, dataset.column_profiles)
        except ProviderCallError as exc:
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
            continue
        except SemanticOutputValidationError as exc:
            db.add(
                _provider_run(
                    dataset=dataset,
                    candidate=candidate,
                    status_value="failed",
                    fallback_from_provider=fallback_from,
                    error_code="AI_PROVIDER_OUTPUT_INVALID",
                    error_message=str(exc),
                    latency_ms=round((time.perf_counter() - started_at) * 1000),
                )
            )
            continue

        _clear_existing_semantic_columns(db, dataset)
        _store_validated_output(db=db, dataset=dataset, output=validated, provider=candidate)
        _finalize_job_run(db, job_run_id, status_value="completed")
        db.add(
            _provider_run(
                dataset=dataset,
                candidate=candidate,
                status_value="completed",
                fallback_from_provider=fallback_from,
                latency_ms=round((time.perf_counter() - started_at) * 1000),
            )
        )
        db.commit()
        return get_semantic_preparation(db, session_id, dataset_id)

    _finalize_job_run(
        db,
        job_run_id,
        status_value="failed",
        error_code="SEMANTIC_PREPARATION_FAILED",
        error_message="AI semantic preparation failed. No fake suggestions were stored.",
    )
    db.commit()
    dataset = _load_dataset_for_session(db, session_id, dataset_id)
    return semantic_preparation_summary_from_dataset(dataset, prefer_latest_failure=True)


def _semantic_mapping_error(message: str) -> AppError:
    return AppError(
        error_code="SEMANTIC_MAPPING_INVALID",
        failed_step="semantic_mapping",
        message=message,
        next_action="Use safe names and approved semantic roles, then retry.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def update_semantic_column_mappings(
    db: Session,
    session_id: str | None,
    dataset_id: str,
    patch: SemanticColumnMappingPatchRequest,
) -> SemanticPreparationResponse:
    dataset = _load_dataset_for_session(db, session_id, dataset_id)
    _ensure_dataset_has_profiles(dataset)
    if not patch.columns:
        raise _semantic_mapping_error("At least one column mapping is required.")

    profiles_by_id = {profile.id: profile for profile in dataset.column_profiles}
    semantic_by_profile_id = {
        semantic.column_profile_id: semantic for semantic in dataset.semantic_columns
    }

    for update in patch.columns:
        profile = profiles_by_id.get(update.column_profile_id)
        if profile is None:
            raise _semantic_mapping_error("Column profile does not belong to this dataset.")
        approved_name = update.approved_name.strip()
        if not SAFE_NAME_RE.fullmatch(approved_name):
            raise _semantic_mapping_error("Approved name must be safe snake-case style text.")
        approved_role = update.approved_role.strip()
        if approved_role not in ALLOWED_SEMANTIC_ROLES:
            raise _semantic_mapping_error("Approved semantic role is not supported.")

        semantic_column = semantic_by_profile_id.get(profile.id)
        if semantic_column is None:
            semantic_column = SemanticColumn(
                dataset=dataset,
                column_profile=profile,
                raw_column_name=profile.raw_column_name,
                suggested_name=approved_name,
                semantic_role=approved_role,
                confidence=0.0,
                needs_review=False,
                reason="Manual mapping saved before AI suggestions were generated.",
            )
            db.add(semantic_column)
            semantic_by_profile_id[profile.id] = semantic_column

        semantic_column.approved_name = approved_name
        semantic_column.approved_role = approved_role
        semantic_column.include_in_model = update.include_in_model
        semantic_column.user_edited = True

    db.commit()
    return get_semantic_preparation(db, session_id, dataset_id)
