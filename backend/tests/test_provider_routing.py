from types import SimpleNamespace

from app.services import (
    analysis_run_service,
    insight_generation_service,
    modeling_proposal_service,
    question_suggestion_service,
    semantic_preparation_service,
)


def config():
    return SimpleNamespace(
        gemini_api_key_1="gemini-key-1",
        gemini_api_key_2="gemini-key-2",
        gemini_model_1="gemini-model-1",
        gemini_model_2="gemini-model-2",
        openai_api_key="openai-key",
        openai_model="openai-model",
    )


def signature(candidates):
    return [
        (candidate.lane_name, candidate.provider_name, candidate.api_key, candidate.model)
        for candidate in candidates
    ]


GEMINI_MODEL_1_KEYS = [
    ("gemini_model_1_key_1", "gemini", "gemini-key-1", "gemini-model-1"),
    ("gemini_model_1_key_2", "gemini", "gemini-key-2", "gemini-model-1"),
]
GEMINI_MODEL_2_KEYS = [
    ("gemini_model_2_key_1", "gemini", "gemini-key-1", "gemini-model-2"),
    ("gemini_model_2_key_2", "gemini", "gemini-key-2", "gemini-model-2"),
]
OPENAI_FALLBACK = [("openai_fallback", "openai", "openai-key", "openai-model")]


def test_semantic_question_analysis_and_insight_use_final_fallback_order() -> None:
    expected = [*GEMINI_MODEL_1_KEYS, *OPENAI_FALLBACK, *GEMINI_MODEL_2_KEYS]

    assert signature(semantic_preparation_service.provider_candidates(config())) == expected
    assert signature(question_suggestion_service.provider_candidates(config())) == expected
    assert signature(analysis_run_service.provider_candidates(config())) == expected
    assert signature(insight_generation_service.provider_candidates(config())) == expected


def test_modeling_proposal_uses_modeling_specific_fallback_order() -> None:
    assert signature(modeling_proposal_service.provider_candidates(config())) == [
        *GEMINI_MODEL_1_KEYS,
        *GEMINI_MODEL_2_KEYS,
        *OPENAI_FALLBACK,
    ]
