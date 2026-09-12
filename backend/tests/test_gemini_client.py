"""
Agent 63 – Test Suite: Gemini Client
Tests MockGeminiClient deterministic responses, error simulations,
and production client configuration validation.
"""

import pytest

from backend.app.core.errors import (
    GeminiConfigurationError,
    GeminiError,
    GeminiTimeoutError,
)
from backend.app.schemas.intent import IntentType, StructuredIntent
from backend.app.services.gemini_client import (
    GeminiClient,
    MockGeminiClient,
    get_gemini_client,
)


def test_mock_gemini_client_success():
    """MockGeminiClient returns canned StructuredIntent and tracks call history."""
    client = MockGeminiClient()
    intent = client.generate_intent(
        user_message="What is the CSE attendance?",
        system_instruction="System instructions...",
    )
    assert intent.intent_type == IntentType.METRIC_QUERY
    assert intent.primary_metric_id == "attendance.percentage"
    assert len(client.call_history) == 1
    assert client.call_history[0]["user_message"] == "What is the CSE attendance?"


def test_mock_gemini_client_custom_intent():
    """MockGeminiClient allows queueing custom canned intents."""
    client = MockGeminiClient()
    custom = StructuredIntent(
        intent_type=IntentType.OUT_OF_SCOPE,
        primary_metric_id=None,
        reasoning_summary="Irrelevant prompt",
    )
    client.set_canned_intent(custom)

    result = client.generate_intent(
        user_message="Who won the cricket match?",
        system_instruction="",
    )
    assert result.intent_type == IntentType.OUT_OF_SCOPE
    assert result.primary_metric_id is None


def test_mock_gemini_client_timeout_simulation():
    """MockGeminiClient simulates timeout exception."""
    client = MockGeminiClient()
    client.set_timeout(True)

    with pytest.raises(GeminiTimeoutError) as exc_info:
        client.generate_intent(user_message="test", system_instruction="")
    assert "timed out" in str(exc_info.value)


def test_mock_gemini_client_error_simulation():
    """MockGeminiClient simulates API error exception."""
    client = MockGeminiClient()
    client.set_error("Simulated 500 Bad Gateway from upstream")

    with pytest.raises(GeminiError) as exc_info:
        client.generate_intent(user_message="test", system_instruction="")
    assert "Simulated 500" in str(exc_info.value)


def test_gemini_client_missing_key_fails_closed(monkeypatch):
    """Production GeminiClient fails closed if GEMINI_API_KEY is not set."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    client = GeminiClient()
    assert client.is_configured is False

    with pytest.raises(GeminiConfigurationError) as exc_info:
        client.generate_intent(user_message="test", system_instruction="")
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)
