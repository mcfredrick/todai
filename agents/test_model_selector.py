"""Tests for model_selector logic."""

import pytest

from model_selector import parse_param_count, pick_writing_model, pick_research_model, FALLBACK_MODEL


# --- parse_param_count ---

@pytest.mark.parametrize("model_id,expected", [
    ("meta-llama/llama-3.3-70b-instruct:free",       70),
    ("google/gemma-3-27b-it:free",                   27),
    ("qwen/qwen3-235b-a22b:free",                   235),  # largest match wins
    ("meta-llama/llama-3.2-1b-instruct:free",         1),
    ("meta-llama/llama-3.1-405b-instruct:free",      405),
    ("mistralai/mistral-small-3.1-24b-instruct:free", 24),
    ("microsoft/phi-4:free",                           0),  # no B count in name
    ("deepseek/deepseek-r1:free",                      0),  # no explicit B count
    ("google/gemini-2.0-flash-exp:free",               0),
])
def test_parse_param_count(model_id, expected):
    assert parse_param_count(model_id) == expected


# --- pick_writing_model ---

def _model(model_id: str) -> dict:
    return {"id": model_id, "context_length": 8192}


def test_pick_writing_model_prefers_higher_tier():
    models = [
        _model("qwen/qwen2.5-72b-instruct:free"),
        _model("meta-llama/llama-3.3-70b-instruct:free"),  # higher tier
    ]
    assert pick_writing_model(models) == "meta-llama/llama-3.3-70b-instruct:free"


def test_pick_writing_model_prefers_larger_params_within_tier():
    models = [
        _model("qwen/qwen2.5-7b-instruct:free"),
        _model("qwen/qwen2.5-72b-instruct:free"),
    ]
    assert pick_writing_model(models) == "qwen/qwen2.5-72b-instruct:free"


def test_pick_writing_model_falls_back_to_largest_context_when_no_tier_match():
    models = [
        {"id": "org/unknown-model-a:free", "context_length": 4096},
        {"id": "org/unknown-model-b:free", "context_length": 32768},
    ]
    assert pick_writing_model(models) == "org/unknown-model-b:free"


def test_pick_writing_model_returns_fallback_when_no_models():
    assert pick_writing_model([]) == FALLBACK_MODEL


# --- pick_research_model ---

def test_pick_research_model_returns_largest_context():
    models = [
        {"id": "org/model-a:free", "context_length": 8192},
        {"id": "org/model-b:free", "context_length": 131072},
        {"id": "org/model-c:free", "context_length": 32768},
    ]
    assert pick_research_model(models) == "org/model-b:free"


def test_pick_research_model_returns_fallback_when_no_models():
    assert pick_research_model([]) == FALLBACK_MODEL
