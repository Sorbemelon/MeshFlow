from __future__ import annotations

from app.models.dataset import AiProviderRun, Dataset, DatasetQuestionSuggestion
from app.schemas.dataset import (
    DatasetQuestionSuggestionSummary,
    ProviderRunSummary,
    QuestionSuggestionsResponse,
)


TASK_TYPE = "dataset_question_suggestions"


def _question_summary(question: DatasetQuestionSuggestion) -> DatasetQuestionSuggestionSummary:
    return DatasetQuestionSuggestionSummary(
        id=question.id,
        question=question.question,
        intent=question.intent,
        sort_order=question.sort_order,
        provider_name=question.provider_name,
        provider_model=question.provider_model,
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


def question_suggestions_summary_from_dataset(dataset: Dataset) -> QuestionSuggestionsResponse:
    task_runs = [
        run for run in dataset.provider_runs if run.task_type == TASK_TYPE
    ]
    suggestions = list(dataset.question_suggestions)

    if suggestions:
        status = "completed"
        message = "Suggested questions are available from the Data Mart catalog."
        next_action = None
    elif dataset.status != "ready_for_analysis":
        status = "not_started"
        message = "Question suggestions wait until dbt Data Marts are ready."
        next_action = "Transform the dataset into Data Marts before using prepared questions."
    elif task_runs:
        latest_run = task_runs[-1]
        status = "failed"
        message = (
            latest_run.error_message
            or "MeshFlow could not generate suggested questions from the Data Marts."
        )
        next_action = "Check AI provider configuration or retry the transformation."
    else:
        status = "not_started"
        message = "Question suggestions have not been generated from Data Marts yet."
        next_action = "Run or retry the dbt transformation to generate prepared questions."

    return QuestionSuggestionsResponse(
        status=status,
        message=message,
        suggestions=[_question_summary(question) for question in suggestions],
        provider_runs=[_provider_run_summary(run) for run in task_runs],
        next_action=next_action,
    )
