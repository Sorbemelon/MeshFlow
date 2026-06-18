from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.dataset import AiProviderRun, AnalysisInsight, AnalysisRun, AnalysisRunChart
from app.services.semantic_preparation_service import (
    ProviderCallError,
    ProviderCandidate,
    call_gemini_provider,
    call_openai_provider,
    gemini_key_candidates,
    openai_candidate,
)


TASK_TYPE = "insight_generation"
TEMPERATURE = 0.2
MAX_FINDINGS = 5
MAX_CHART_INSIGHTS = 3
SECRET_MARKERS = ("api_key", "secret", "password", "token")
CONFIDENCE_VALUES = {"low", "medium", "high"}
ALLOWED_TAGS = {
    "trend",
    "breakdown",
    "anomaly",
    "kpi",
    "comparison",
    "recommendation",
    "data_quality",
    "revenue",
    "product",
    "customer",
    "store",
    "table",
}


class InsightOutputValidationError(Exception):
    pass


@dataclass(frozen=True)
class ValidatedInsight:
    insight_level: str
    summary: str
    key_findings: list[str]
    tags: list[str]
    confidence: str
    chart: AnalysisRunChart | None = None


@dataclass(frozen=True)
class InsightGenerationResult:
    status: str
    message: str | None


def provider_candidates(config: Settings = settings) -> list[ProviderCandidate]:
    return [
        *gemini_key_candidates("gemini_model_1", config.gemini_model_1, config),
        openai_candidate("openai_fallback", config),
        *gemini_key_candidates("gemini_model_2", config.gemini_model_2, config),
    ]


def _safe_text(value: Any, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise InsightOutputValidationError("Expected a string value.")
    text = re.sub(r"\s+", " ", value.strip())
    if not text or len(text) > max_length:
        raise InsightOutputValidationError("String value is empty or too long.")
    return text


def _contains_secret(value: object) -> bool:
    text = json.dumps(value, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _contains_unsupported_claim(text: str) -> bool:
    lowered = text.lower()
    unsupported_phrases = (
        "entire dataset",
        "complete dataset",
        "all customers",
        "all products",
        "caused by",
        "proves that",
    )
    return any(phrase in lowered for phrase in unsupported_phrases)


def _findings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InsightOutputValidationError("Key findings must be a list.")
    findings: list[str] = []
    for item in value[:MAX_FINDINGS]:
        finding = _safe_text(item, max_length=240)
        if _contains_unsupported_claim(finding):
            raise InsightOutputValidationError("Insight finding makes an unsupported claim.")
        findings.append(finding)
    return findings


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InsightOutputValidationError("Tags must be a list.")
    tags: list[str] = []
    for item in value:
        tag = _safe_text(item, max_length=32).lower().replace(" ", "_")
        if tag not in ALLOWED_TAGS:
            raise InsightOutputValidationError("Insight tag is not allowed.")
        if tag not in tags:
            tags.append(tag)
    return tags


def _confidence(value: Any) -> str:
    confidence = _safe_text(value, max_length=16).lower()
    if confidence not in CONFIDENCE_VALUES:
        raise InsightOutputValidationError("Insight confidence is not allowed.")
    return confidence


def _chart_lookup(charts: list[AnalysisRunChart]) -> dict[str, AnalysisRunChart]:
    lookup: dict[str, AnalysisRunChart] = {}
    for chart in charts:
        lookup[chart.id] = chart
        lookup[chart.title.lower()] = chart
    return lookup


def _validate_question_insight(value: Any) -> ValidatedInsight:
    if not isinstance(value, dict):
        raise InsightOutputValidationError("Question insight must be an object.")
    summary = _safe_text(value.get("summary"), max_length=800)
    if _contains_unsupported_claim(summary):
        raise InsightOutputValidationError("Insight summary makes an unsupported claim.")
    return ValidatedInsight(
        insight_level="question",
        summary=summary,
        key_findings=_findings(value.get("key_findings", [])),
        tags=_tags(value.get("tags", [])),
        confidence=_confidence(value.get("confidence")),
    )


def _validate_chart_insight(
    value: Any,
    *,
    charts: list[AnalysisRunChart],
    lookup: dict[str, AnalysisRunChart],
) -> ValidatedInsight:
    if not isinstance(value, dict):
        raise InsightOutputValidationError("Chart insight must be an object.")
    chart_key = value.get("chart_id") or value.get("analysis_run_chart_id")
    if not isinstance(chart_key, str) or not chart_key.strip():
        chart_key = value.get("chart_title")
    if not isinstance(chart_key, str) or not chart_key.strip():
        raise InsightOutputValidationError("Chart insight must reference a chart.")
    chart = lookup.get(chart_key.strip()) or lookup.get(chart_key.strip().lower())
    if chart is None:
        raise InsightOutputValidationError("Chart insight does not map to a stored chart.")
    if chart not in charts:
        raise InsightOutputValidationError("Chart insight references an unknown chart.")
    summary = _safe_text(value.get("summary"), max_length=800)
    if _contains_unsupported_claim(summary):
        raise InsightOutputValidationError("Chart insight summary makes an unsupported claim.")
    return ValidatedInsight(
        insight_level="chart",
        summary=summary,
        key_findings=_findings(value.get("key_findings", [])),
        tags=_tags(value.get("tags", [])),
        confidence=_confidence(value.get("confidence")),
        chart=chart,
    )


def validate_insight_output(
    raw_text: str,
    *,
    charts: list[AnalysisRunChart],
) -> list[ValidatedInsight]:
    if _contains_secret(raw_text):
        raise InsightOutputValidationError("Provider output included secret-like text.")
    try:
        body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise InsightOutputValidationError("Provider output was not valid JSON.") from exc
    if not isinstance(body, dict):
        raise InsightOutputValidationError("Provider output must be a JSON object.")

    insights = [_validate_question_insight(body.get("question_insight"))]
    chart_values = body.get("chart_insights", [])
    if not isinstance(chart_values, list):
        raise InsightOutputValidationError("Chart insights must be a list.")
    lookup = _chart_lookup(charts)
    for item in chart_values[:MAX_CHART_INSIGHTS]:
        insights.append(_validate_chart_insight(item, charts=charts, lookup=lookup))
    return insights


def _chart_context(chart: AnalysisRunChart) -> dict[str, object]:
    return {
        "chart_id": chart.id,
        "title": chart.title,
        "chart_type": chart.chart_type,
        "source_model": chart.source_model,
        "metric_summary": chart.metric_summary,
        "dimension_summary": chart.dimension_summary,
        "chart_spec": chart.chart_spec_json,
        "chart_data": chart.data_json[:100],
    }


def build_insight_prompt(analysis_run: AnalysisRun) -> str:
    preview_rows = (analysis_run.preview_rows_json or [])[:100]
    context = {
        "question": analysis_run.question,
        "dataset": {
            "id": analysis_run.dataset_id,
            "name": analysis_run.dataset.name if analysis_run.dataset else None,
            "source_type": analysis_run.dataset.source_type if analysis_run.dataset else None,
        },
        "analysis": {
            "id": analysis_run.id,
            "source_model": analysis_run.source_model,
            "grain": analysis_run.grain,
            "metrics": analysis_run.metrics_json or [],
            "dimensions": analysis_run.dimensions_json or [],
            "generated_sql": analysis_run.generated_sql,
            "output_schema": analysis_run.output_schema_json or [],
            "preview_rows": preview_rows,
            "row_count": analysis_run.row_count,
        },
        "charts": [_chart_context(chart) for chart in analysis_run.charts],
        "insight_priorities": [
            "Summarize what the previewed result directly shows.",
            "Name the metric and dimension driving each finding.",
            "Call out trends, rankings, unusually high or low values, or concentration only when visible in rows/charts.",
            "Use medium confidence unless the preview rows are comprehensive and the pattern is obvious.",
            "Use low confidence when the result has few rows or limited context.",
            "Keep recommendations cautious and tied to observed results.",
        ],
        "known_limits": [
            "Use only the stored preview rows and chart snapshots.",
            "Do not claim facts beyond the previewed result.",
            "Do not claim causation unless the result directly supports it.",
            "Do not claim analysis covers the full dataset unless row_count and preview rows prove that.",
            "Do not mention backend internals, SQL execution details, provider routing, or dashboard persistence.",
            f"Preview rows supplied: {len(preview_rows)}.",
        ],
    }
    schema = {
        "question_insight": {
            "summary": "short evidence-backed summary",
            "key_findings": ["concise finding grounded in preview rows"],
            "tags": ["one_or_more_allowed_tag_strings"],
            "confidence": "exactly one of: low, medium, high",
        },
        "chart_insights": [
            {
                "chart_id": "existing chart_id from context",
                "chart_title": "existing chart title from context",
                "summary": "short chart-level summary",
                "key_findings": ["concise finding grounded in chart data"],
                "tags": ["one_or_more_allowed_tag_strings"],
                "confidence": "exactly one of: low, medium, high",
            }
        ],
        "warnings": [],
    }
    return (
        "You are generating MeshFlow insights from completed Snowflake analysis output.\n"
        "Return JSON only. Do not include markdown.\n"
        "Use only the supplied output schema, preview rows, and chart snapshots.\n"
        "Do not invent rows, metrics, charts, dashboard cards, or external facts.\n"
        "Do not claim the preview represents the entire dataset unless the context says so.\n"
        "Keep findings concise, evidence-backed, and useful to a business user.\n"
        "Every key finding must be traceable to a metric, dimension, row, or chart in context.\n"
        "Prefer neutral language over certainty when the preview is small.\n"
        "For confidence, return exactly one string: low, medium, or high. Do not return an array.\n"
        "For tags, return an array containing only allowed tag strings.\n"
        f"Allowed tags: {', '.join(sorted(ALLOWED_TAGS))}.\n"
        f"Output schema: {json.dumps(schema, separators=(',', ':'))}\n"
        f"Context: {json.dumps(context, default=str, separators=(',', ':'))}"
    )


def _call_provider(candidate: ProviderCandidate, prompt: str) -> str:
    if candidate.provider_name == "gemini":
        return call_gemini_provider(candidate, prompt, TEMPERATURE)
    return call_openai_provider(candidate, prompt, TEMPERATURE)


def _provider_run(
    *,
    analysis_run: AnalysisRun,
    candidate: ProviderCandidate,
    status_value: str,
    fallback_from_provider: str | None,
    error_code: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
) -> AiProviderRun:
    return AiProviderRun(
        dataset=analysis_run.dataset,
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


def _store_insights(
    db: Session,
    analysis_run: AnalysisRun,
    *,
    insights: list[ValidatedInsight],
    provider: ProviderCandidate,
) -> None:
    for insight in insights:
        db.add(
            AnalysisInsight(
                analysis_run=analysis_run,
                chart=insight.chart,
                insight_level=insight.insight_level,
                status="completed",
                summary=insight.summary,
                key_findings_json=insight.key_findings,
                tags_json=insight.tags,
                confidence=insight.confidence,
                provider_name=provider.lane_name,
                provider_model=provider.model,
            )
        )


def _store_failed_insight(
    db: Session,
    analysis_run: AnalysisRun,
    *,
    error_code: str,
    error_message: str,
) -> None:
    db.add(
        AnalysisInsight(
            analysis_run=analysis_run,
            insight_level="question",
            status="failed",
            error_code=error_code,
            error_message=error_message,
        )
    )


def insight_summary(insight: AnalysisInsight) -> dict[str, Any]:
    return {
        "id": insight.id,
        "analysis_run_id": insight.analysis_run_id,
        "analysis_run_chart_id": insight.analysis_run_chart_id,
        "insight_level": insight.insight_level,
        "status": insight.status,
        "summary": insight.summary,
        "key_findings": insight.key_findings_json or [],
        "tags": insight.tags_json or [],
        "confidence": insight.confidence,
        "provider_name": insight.provider_name,
        "provider_model": insight.provider_model,
        "error_code": insight.error_code,
        "error_message": insight.error_message,
        "created_at": insight.created_at.isoformat(),
        "updated_at": insight.updated_at.isoformat(),
    }


def insight_status_for_run(analysis_run: AnalysisRun) -> str:
    if any(insight.status == "completed" for insight in analysis_run.insights):
        return "completed"
    if any(insight.status == "failed" for insight in analysis_run.insights):
        return "failed"
    return "not_started"


def ensure_analysis_insights(
    db: Session,
    analysis_run: AnalysisRun,
    *,
    config: Settings = settings,
) -> InsightGenerationResult:
    if analysis_run.status != "completed":
        return InsightGenerationResult(status="not_started", message=None)
    if any(insight.status == "completed" for insight in analysis_run.insights):
        return InsightGenerationResult(status="completed", message=None)
    if any(insight.status == "failed" for insight in analysis_run.insights):
        failed = next(insight for insight in analysis_run.insights if insight.status == "failed")
        return InsightGenerationResult(status="failed", message=failed.error_message)
    if not analysis_run.charts:
        return InsightGenerationResult(
            status="failed",
            message="Analysis completed, but no chart snapshots are available for insight generation.",
        )

    prompt = build_insight_prompt(analysis_run)
    previous_lane: str | None = None
    saw_configured_provider = False
    latest_error = "Analysis completed, but MeshFlow could not generate insights from the result preview."
    for candidate in provider_candidates(config):
        fallback_from = previous_lane
        previous_lane = candidate.lane_name

        if not candidate.api_key or not candidate.model:
            db.add(
                _provider_run(
                    analysis_run=analysis_run,
                    candidate=candidate,
                    status_value="unavailable",
                    fallback_from_provider=fallback_from,
                    error_code="INSIGHT_PROVIDER_NOT_CONFIGURED",
                    error_message=f"{candidate.lane_name} is not configured.",
                )
            )
            db.flush()
            continue

        saw_configured_provider = True
        started_at = time.perf_counter()
        try:
            provider_output = _call_provider(candidate, prompt)
            validated = validate_insight_output(provider_output, charts=list(analysis_run.charts))
        except ProviderCallError as exc:
            latest_error = exc.message
            db.add(
                _provider_run(
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
        except InsightOutputValidationError as exc:
            latest_error = str(exc)
            db.add(
                _provider_run(
                    analysis_run=analysis_run,
                    candidate=candidate,
                    status_value="failed",
                    fallback_from_provider=fallback_from,
                    error_code="INSIGHT_PROVIDER_OUTPUT_INVALID",
                    error_message=str(exc),
                    latency_ms=round((time.perf_counter() - started_at) * 1000),
                )
            )
            db.flush()
            continue

        _store_insights(db, analysis_run, insights=validated, provider=candidate)
        db.add(
            _provider_run(
                analysis_run=analysis_run,
                candidate=candidate,
                status_value="completed",
                fallback_from_provider=fallback_from,
                latency_ms=round((time.perf_counter() - started_at) * 1000),
            )
        )
        db.flush()
        return InsightGenerationResult(status="completed", message=None)

    error_code = (
        "INSIGHT_GENERATION_FAILED"
        if saw_configured_provider
        else "INSIGHT_PROVIDER_NOT_CONFIGURED"
    )
    _store_failed_insight(
        db,
        analysis_run,
        error_code=error_code,
        error_message=(
            "Analysis completed, but MeshFlow could not generate insights from the result preview."
            if saw_configured_provider
            else "Analysis completed, but no insight provider is configured."
        ),
    )
    db.flush()
    return InsightGenerationResult(
        status="failed",
        message=(
            "Analysis completed, but no insight provider is configured."
            if not saw_configured_provider
            else latest_error
        ),
    )
