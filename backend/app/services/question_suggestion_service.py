from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.dataset import AiProviderRun, Dataset, DatasetQuestionSuggestion
from app.services.analysis_run_service import analysis_catalog_for_dataset
from app.services.semantic_preparation_service import (
    ProviderCallError,
    ProviderCandidate,
    call_gemini_provider,
    call_openai_provider,
    gemini_key_candidates,
    openai_candidate,
)


TASK_TYPE = "dataset_question_suggestions"
TEMPERATURE = 0.1
MAX_QUESTIONS = 5
SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
RAW_ONLY_TERMS = {
    "payment",
    "payment method",
    "discount",
    "discount amount",
    "unit price",
    "cost",
    "customer name",
    "customer id",
    "product id",
    "store id",
    "order id",
    "order line",
    "raw",
}


class QuestionSuggestionValidationError(Exception):
    pass


@dataclass(frozen=True)
class ValidatedQuestionSuggestion:
    question: str
    intent: str | None


@dataclass(frozen=True)
class QuestionSuggestionGenerationResult:
    status: str
    message: str | None
    question_count: int = 0


def provider_candidates(config: Settings = settings) -> list[ProviderCandidate]:
    return [
        *gemini_key_candidates("gemini_model_1", config.gemini_model_1, config),
        openai_candidate("openai_fallback", config),
        *gemini_key_candidates("gemini_model_2", config.gemini_model_2, config),
    ]


def _catalog_terms(catalog: dict[str, dict[str, object]]) -> set[str]:
    terms: set[str] = {
        "sales",
        "performance",
        "trend",
        "monthly",
        "month",
        "compare",
        "comparison",
        "breakdown",
    }
    for model_name, info in catalog.items():
        terms.add(model_name.lower())
        for collection_name in ("metrics", "dimensions"):
            values = info.get(collection_name, [])
            if not isinstance(values, list):
                continue
            for value in values:
                normalized = str(value).lower()
                terms.add(normalized)
                terms.update(part for part in normalized.split("_") if part)
    return terms


def build_question_suggestion_prompt(
    *,
    dataset: Dataset,
    catalog: dict[str, dict[str, object]] | None = None,
) -> str:
    effective_catalog = catalog or analysis_catalog_for_dataset(dataset)
    catalog_summary = {
        model_name: {
            "grain": info.get("grain"),
            "dimensions": info.get("dimensions", []),
            "metrics": info.get("metrics", []),
        }
        for model_name, info in effective_catalog.items()
    }
    context = {
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "source_type": dataset.source_type,
            "status": dataset.status,
            "row_count": dataset.row_count,
        },
        "available_data_marts": catalog_summary,
        "question_priorities": [
            "Ask questions a business user would naturally run on a dashboard.",
            "Prefer trends, breakdowns, comparisons, and top/bottom performance questions.",
            "Each question should map clearly to one available Data Mart.",
            "Prefer questions that use exposed metrics and dimensions together.",
            "Avoid schema, setup, raw-column, data-quality, or implementation questions.",
        ],
        "hard_limits": [
            "Return JSON only.",
            "Use only the Data Mart models, metrics, dimensions, and grains in context.",
            "Do not reference raw-only fields that are not exposed by the Data Marts.",
            "Do not generate SQL, charts, insights, or dashboard cards.",
            "Do not claim analysis has already run.",
            "Do not ask questions requiring multiple marts unless one mart clearly exposes all needed fields.",
            "Avoid duplicate questions or questions that differ only by wording.",
            f"Return at most {MAX_QUESTIONS} questions.",
        ],
    }
    schema = {
        "suggested_questions": [
            {
                "question": "concise question answerable from the available Data Marts",
                "intent": "safe_snake_case_intent",
            }
        ],
        "warnings": [],
    }
    return (
        "You are generating MeshFlow suggested analysis questions after dbt Data Marts "
        "have been built.\n"
        "Return JSON only. Do not include markdown.\n"
        "Every question must be answerable from the available Data Marts in context.\n"
        "Prefer practical business questions over schema-inspection questions.\n"
        "Make questions concise, specific, and directly aligned with exposed metrics and dimensions.\n"
        "Use the intent field to name the analysis goal in safe snake_case.\n"
        "Do not invent raw columns, marts, metrics, dimensions, analyses, charts, or insights.\n"
        f"Output schema: {json.dumps(schema, separators=(',', ':'))}\n"
        f"Context: {json.dumps(context, separators=(',', ':'))}"
    )


def _safe_text(value: Any, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise QuestionSuggestionValidationError("Expected a string value.")
    text = re.sub(r"\s+", " ", value.strip())
    if not text or len(text) > max_length:
        raise QuestionSuggestionValidationError("String value is empty or too long.")
    return text


def _validate_question(value: Any, catalog_terms: set[str]) -> ValidatedQuestionSuggestion:
    if not isinstance(value, dict):
        raise QuestionSuggestionValidationError("Suggested question must be an object.")
    question = _safe_text(value.get("question"), max_length=180)
    lowered = question.lower()
    if "?" not in question:
        raise QuestionSuggestionValidationError("Suggested questions must be phrased as questions.")
    if any(term in lowered for term in RAW_ONLY_TERMS):
        raise QuestionSuggestionValidationError(
            "Suggested question references fields outside the Data Mart catalog."
        )
    if not any(term in lowered for term in catalog_terms):
        raise QuestionSuggestionValidationError(
            "Suggested question does not reference available Data Mart concepts."
        )
    if re.search(r"(dashboard|chart|insight).{0,40}(ready|created|generated)", lowered):
        raise QuestionSuggestionValidationError("Suggested question claims a future artifact is ready.")
    intent_value = value.get("intent")
    intent = None
    if intent_value is not None:
        intent = _safe_text(intent_value, max_length=128)
        if not SAFE_NAME_RE.fullmatch(intent):
            raise QuestionSuggestionValidationError("Suggested question intent is not safe.")
    return ValidatedQuestionSuggestion(question=question, intent=intent)


def validate_question_suggestion_output(
    raw_text: str,
    *,
    catalog: dict[str, dict[str, object]],
) -> list[ValidatedQuestionSuggestion]:
    lowered = raw_text.lower()
    if "api_key" in lowered or "secret" in lowered:
        raise QuestionSuggestionValidationError("Provider output included secret-like text.")
    try:
        body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise QuestionSuggestionValidationError("Provider output was not valid JSON.") from exc
    if not isinstance(body, dict):
        raise QuestionSuggestionValidationError("Provider output must be a JSON object.")
    question_values = body.get("suggested_questions")
    if not isinstance(question_values, list) or not question_values:
        raise QuestionSuggestionValidationError("Provider output must include suggested_questions.")

    catalog_terms = _catalog_terms(catalog)
    suggestions: list[ValidatedQuestionSuggestion] = []
    seen_questions: set[str] = set()
    for value in question_values[:MAX_QUESTIONS]:
        suggestion = _validate_question(value, catalog_terms)
        key = suggestion.question.lower()
        if key in seen_questions:
            continue
        seen_questions.add(key)
        suggestions.append(suggestion)

    if not suggestions:
        raise QuestionSuggestionValidationError("Provider output did not include unique questions.")
    return suggestions


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


def _clear_existing_questions(db: Session, dataset: Dataset) -> None:
    for question in list(dataset.question_suggestions):
        db.delete(question)
    dataset.question_suggestions.clear()
    db.flush()


def _store_questions(
    db: Session,
    dataset: Dataset,
    questions: list[ValidatedQuestionSuggestion],
    provider: ProviderCandidate,
) -> None:
    for index, question in enumerate(questions):
        db.add(
            DatasetQuestionSuggestion(
                dataset=dataset,
                question=question.question,
                intent=question.intent,
                sort_order=index,
                provider_name=provider.provider_name,
                provider_model=provider.model,
            )
        )


def generate_dataset_question_suggestions(
    db: Session,
    dataset: Dataset,
    *,
    catalog: dict[str, dict[str, object]] | None = None,
    force: bool = False,
    config: Settings = settings,
) -> QuestionSuggestionGenerationResult:
    if dataset.status != "ready_for_analysis":
        return QuestionSuggestionGenerationResult(
            status="not_started",
            message="Question suggestions wait until dbt Data Marts are ready.",
        )

    effective_catalog = catalog or analysis_catalog_for_dataset(dataset)
    if not effective_catalog:
        return QuestionSuggestionGenerationResult(
            status="failed",
            message="No reliable Data Mart catalog is available for suggested questions.",
        )
    if dataset.question_suggestions and not force:
        return QuestionSuggestionGenerationResult(
            status="completed",
            message="Suggested questions are already available.",
            question_count=len(dataset.question_suggestions),
        )

    _clear_existing_questions(db, dataset)
    prompt = build_question_suggestion_prompt(dataset=dataset, catalog=effective_catalog)
    previous_lane: str | None = None
    latest_error = "MeshFlow could not generate suggested questions from the Data Marts."
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
            validated = validate_question_suggestion_output(
                provider_output,
                catalog=effective_catalog,
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
        except QuestionSuggestionValidationError as exc:
            latest_error = str(exc)
            db.add(
                _provider_run(
                    dataset=dataset,
                    candidate=candidate,
                    status_value="failed",
                    fallback_from_provider=fallback_from,
                    error_code="QUESTION_SUGGESTION_OUTPUT_INVALID",
                    error_message=str(exc),
                    latency_ms=round((time.perf_counter() - started_at) * 1000),
                )
            )
            db.flush()
            continue

        _store_questions(db, dataset, validated, candidate)
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
        return QuestionSuggestionGenerationResult(
            status="completed",
            message="Suggested questions were generated from the Data Marts.",
            question_count=len(validated),
        )

    return QuestionSuggestionGenerationResult(
        status="failed",
        message=(
            latest_error
            if saw_configured_provider
            else "No AI provider is configured for Data Mart question suggestions."
        ),
    )
