"""
Agent 63 – Legacy Google Gemini Client Abstraction (Phase 6)
Retained for backward compatibility and regression test isolation.
Groq (GroqIntentClient via IntentLLMClient) is the sole active Phase 6 intent provider.
Backend-only: API keys and provider interaction are never exposed to the frontend.
Fails closed when API key is missing. Includes mock test client for deterministic CI.
"""

from abc import ABC, abstractmethod
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Union

from backend.app.core.config import settings
from backend.app.core.errors import (
    GeminiConfigurationError,
    GeminiError,
    GeminiTimeoutError,
)
from backend.app.core.logging import get_logger
from backend.app.schemas.intent import (
    IntentType,
    StructuredIntent,
    TimeContext,
)

logger = get_logger("agent63.services.gemini_client")


from backend.app.services.intent_llm_client import IntentLLMClient


class BaseGeminiClient(IntentLLMClient):
    """Abstract contract for Gemini natural language intent generation (Legacy Phase 6)."""

    @abstractmethod
    def generate_intent(self, user_message: str, system_instruction: str) -> StructuredIntent:
        """Submits prompt to Gemini with system instructions and returns validated StructuredIntent."""
        pass


def _build_developer_api_schema() -> Dict[str, Any]:
    """
    Generates a Google GenAI Developer API-compliant OpenAPI schema from StructuredIntent.
    Strips 'additionalProperties' which is rejected by google-genai in non-Vertex mode,
    and explicitly specifies verified dimensional filter keys.
    """
    import copy
    schema = copy.deepcopy(StructuredIntent.model_json_schema())

    def _strip_additional_properties(d: Any) -> None:
        if isinstance(d, dict):
            d.pop("additionalProperties", None)
            d.pop("additional_properties", None)
            for v in d.values():
                _strip_additional_properties(v)
        elif isinstance(d, list):
            for item in d:
                _strip_additional_properties(item)

    _strip_additional_properties(schema)

    # Supply explicit dimension properties for filters so Gemini can populate them in structured mode
    if "properties" in schema and "filters" in schema["properties"]:
        schema["properties"]["filters"]["properties"] = {
            "department": {"type": "string", "description": "Department code or name, e.g. CSE"},
            "department_code": {"type": "string"},
            "department_id": {"type": "string"},
            "academic_year": {"type": "string", "description": "Academic year e.g. 2024-25"},
            "programme": {"type": "string"},
            "programme_code": {"type": "string"},
            "section": {"type": "string"},
            "course": {"type": "string"},
            "course_code": {"type": "string"},
            "gender": {"type": "string"},
            "category": {"type": "string"},
            "regulation": {"type": "string"},
        }

    # Supply explicit date_range properties if present in $defs
    if "$defs" in schema and "TimeContext" in schema["$defs"]:
        tc = schema["$defs"]["TimeContext"]
        if "properties" in tc and "date_range" in tc["properties"]:
            tc["properties"]["date_range"] = {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
            }

    return schema


class GeminiClient(BaseGeminiClient):
    """
    Production client utilizing Google's official GenAI SDK (`google-genai`).
    Enforces deterministic structured JSON output, strict timeout, and error sanitization.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        raw_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        self._api_key = raw_key.strip() if raw_key else ""
        self._model = model or settings.GEMINI_MODEL
        self._timeout_seconds = timeout_seconds or settings.GEMINI_TIMEOUT_SECONDS
        self._client: Optional[Any] = None

        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {type(e).__name__}")

    @property
    def is_configured(self) -> bool:
        """Indicates if API key and client are operational."""
        return bool(self._api_key and self._client)

    def generate_intent(self, user_message: str, system_instruction: str) -> StructuredIntent:
        """
        Invokes Gemini with structured JSON output enforcement using the official SDK.
        Fails closed if the client or API key is unconfigured.
        """
        if not self._client or not self._api_key:
            logger.warning("Gemini intent requested but GEMINI_API_KEY is not configured on backend.")
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured on this server.")

        try:
            from google.genai import types

            schema = _build_developer_api_schema()

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,  # Deterministic intent parsing
            )

            # Map deprecated model identifier to supported model in Google GenAI API
            effective_model = self._model
            if "2.5-flash" in effective_model and "lite" not in effective_model:
                effective_model = "gemini-3.6-flash"

            start_time = time.time()
            response = self._client.models.generate_content(
                model=effective_model,
                contents=user_message,
                config=config,
            )
            elapsed = time.time() - start_time
            logger.info(f"Gemini intent generated in {elapsed:.2f}s using model '{effective_model}'")

            if not response or not response.text:
                raise GeminiError("Received empty response from Google Gemini.")

            raw_text = response.text.strip()
            try:
                parsed_json = json.loads(raw_text)
            except Exception as json_err:
                logger.error(f"Failed to parse Gemini output as JSON: {type(json_err).__name__}: {json_err}")
                raise GeminiError("Failed to parse structured analytical intent from Gemini response.")

            if not isinstance(parsed_json, dict):
                raise GeminiError("Gemini response did not return a valid JSON object.")

            try:
                return StructuredIntent.model_validate(parsed_json)
            except Exception as val_err:
                logger.error(f"Pydantic validation failed for Gemini intent: {type(val_err).__name__}: {val_err}")
                raise GeminiError("Structured output from Gemini could not be validated against intent schema.")

        except TimeoutError:
            logger.error(f"Gemini API request exceeded timeout of {self._timeout_seconds}s")
            raise GeminiTimeoutError(f"Gemini request exceeded configured timeout of {self._timeout_seconds}s.")
        except (GeminiTimeoutError, GeminiConfigurationError, GeminiError):
            raise
        except Exception as e:
            err_name = type(e).__name__
            logger.error(f"Gemini provider error ({err_name}): {str(e)}")
            raise GeminiError("Agent 63's intent service is temporarily unavailable. Please try again.")



class MockGeminiClient(BaseGeminiClient):
    """
    In-memory deterministic test client for unit and integration testing.
    Allows tests to run reliably without live external network calls or real API keys.
    """

    def __init__(self):
        self._responses: Dict[str, StructuredIntent] = {}
        self._default_response: Optional[StructuredIntent] = None
        self._should_timeout: bool = False
        self._should_fail: bool = False
        self._error_message: str = "Mock provider failure"
        self._call_history: List[Dict[str, Any]] = []

    @property
    def is_configured(self) -> bool:
        """Mock client is always configured for testing."""
        return True

    @property
    def call_history(self) -> List[Dict[str, Any]]:
        """Log of calls made to generate_intent during testing."""
        return self._call_history

    def register_response(
        self, user_message_substring: str, response_payload: Union[StructuredIntent, Dict[str, Any]]
    ) -> None:
        """Registers a predefined structured response triggered when user message contains substring."""
        if isinstance(response_payload, dict):
            intent = StructuredIntent.model_validate(response_payload)
        else:
            intent = response_payload
        self._responses[user_message_substring.lower()] = intent

    def set_canned_intent(self, intent: Union[StructuredIntent, Dict[str, Any]]) -> None:
        """Sets fallback response if no registered substring matches."""
        if isinstance(intent, dict):
            self._default_response = StructuredIntent.model_validate(intent)
        else:
            self._default_response = intent

    def set_default_response(self, response_payload: Union[StructuredIntent, Dict[str, Any]]) -> None:
        """Alias for set_canned_intent."""
        self.set_canned_intent(response_payload)

    def set_timeout(self, should_timeout: bool = True) -> None:
        """Toggles simulated upstream timeout."""
        self._should_timeout = should_timeout

    def set_simulate_timeout(self, should_timeout: bool = True) -> None:
        """Alias for set_timeout."""
        self.set_timeout(should_timeout)

    def set_error(self, message: str) -> None:
        """Enables simulated upstream error."""
        self._should_fail = True
        self._error_message = message

    def set_simulate_failure(self, should_fail: bool, message: str = "Mock provider failure") -> None:
        """Alias for set_error."""
        self._should_fail = should_fail
        self._error_message = message

    def generate_intent(self, user_message: str, system_instruction: str) -> StructuredIntent:
        self._call_history.append({
            "user_message": user_message,
            "system_instruction": system_instruction,
        })

        if self._should_timeout:
            raise GeminiTimeoutError("Mock Gemini request timed out.")

        if self._should_fail:
            raise GeminiError(self._error_message)

        # Pattern match
        lower_msg = user_message.lower()
        for pattern, resp in self._responses.items():
            if pattern in lower_msg:
                return resp

        if self._default_response is not None:
            return self._default_response

        # Generic default mock interpretation
        return StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            primary_metric_id="attendance.percentage",
            dimensions=["department"],
            filters={"department": "CSE"},
            time_context=TimeContext(),
            reasoning_summary="Mock extracted default metric query",
        )


# Global client singleton
_gemini_client: Optional[BaseGeminiClient] = None


def get_gemini_client() -> BaseGeminiClient:
    """Returns the configured Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


def set_gemini_client(client: BaseGeminiClient) -> None:
    """Allows injecting mock or custom Gemini client during tests."""
    global _gemini_client
    _gemini_client = client


def reset_gemini_client() -> None:
    """Resets global singleton client for test isolation."""
    global _gemini_client
    _gemini_client = None
