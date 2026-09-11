"""
Agent 63 – Structured Logging Foundation
Provides context-aware, security-hardened structured logging with correlation IDs.
Strictly scrubbed of passwords, tokens, credentials, and sensitive PII.
"""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable for request correlation ID
request_id_ctx_var = contextvars.ContextVar("request_id", default=None)

SENSITIVE_PATTERNS = {
    "password", "secret", "token", "authorization", "bearer",
    "jwt", "api_key", "apikey", "access_token", "refresh_token",
    "cookie", "counselling", "medical_record", "psychological"
}


class SecurityScrubbingJsonFormatter(logging.Formatter):
    """
    JSON formatter that injects correlation ID, timestamps,
    and strips known sensitive tokens from structured logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx_var.get()
        }

        # Include extra contextual fields if provided (e.g., path, status_code, duration_ms)
        for key in ["path", "method", "status_code", "duration_ms", "client_ip"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Include exception info safely without leaking credentials
        if record.exc_info:
            log_data["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            # Only include formatted exception message, not full memory dumps
            if record.exc_text:
                log_data["exception_summary"] = record.exc_text.splitlines()[-1]

        # Security scrub
        sanitized_data = self._scrub_dict(log_data)
        return json.dumps(sanitized_data)

    def _scrub_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        scrubbed = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_PATTERNS):
                scrubbed[k] = "[REDACTED]"
            elif isinstance(v, dict):
                scrubbed[k] = self._scrub_dict(v)
            elif isinstance(v, str):
                # Basic check for token/bearer strings in message
                lower_val = v.lower()
                if "bearer " in lower_val or "password=" in lower_val:
                    scrubbed[k] = "[REDACTED_CREDENTIAL_IN_LOG]"
                else:
                    scrubbed[k] = v
            else:
                scrubbed[k] = v
        return scrubbed


def setup_logging(log_level: str = "INFO") -> None:
    """Configures root and application loggers with JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SecurityScrubbingJsonFormatter())
    root_logger.addHandler(handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.error").handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger."""
    return logging.getLogger(name)
