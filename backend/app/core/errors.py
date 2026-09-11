"""
Agent 63 – Centralized Error Handling
Provides unified application exception hierarchy and FastAPI exception handlers.
Ensures consistent JSON error format and prevents leaking internal stack traces,
SQL queries, filesystem paths, or credentials to API clients.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.logging import get_logger, request_id_ctx_var

logger = get_logger("agent63.errors")


class AppException(Exception):
    """Base application exception for all domain and operational errors."""

    def __init__(
        self,
        code: str = "APPLICATION_ERROR",
        message: str = "An application error occurred.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundError(AppException):
    def __init__(self, message: str = "Requested resource not found.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConfigurationError(AppException):
    def __init__(self, message: str = "Configuration error.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="CONFIGURATION_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class SchemaRegistryError(AppException):
    def __init__(self, message: str = "Schema registry failure.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SCHEMA_REGISTRY_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class SemanticRegistryError(AppException):
    def __init__(self, message: str = "Semantic registry failure.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SEMANTIC_REGISTRY_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "Access denied.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AUTHORIZATION_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ServiceUnavailableError(AppException):
    def __init__(self, message: str = "Service unavailable.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def _format_error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    current_request_id = request_id_ctx_var.get()
    error_payload: Dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": current_request_id,
    }
    if details:
        error_payload["details"] = details
    return {"error": error_payload}


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles domain-specific application exceptions."""
    logger.warning(
        f"Handled application exception [{exc.code}]: {exc.message}",
        extra={"status_code": exc.status_code, "path": request.url.path}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error_response(code=exc.code, message=exc.message, details=exc.details),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles FastAPI/Pydantic request validation errors without leaking sensitive payload data."""
    logger.warning(
        "Request validation error",
        extra={"status_code": status.HTTP_422_UNPROCESSABLE_ENTITY, "path": request.url.path}
    )
    # Sanitize validation errors: omit input values to avoid credential echo
    clean_errors = []
    for err in exc.errors():
        clean_errors.append({
            "loc": err.get("loc", []),
            "msg": err.get("msg", "Invalid value"),
            "type": err.get("type", "validation_error")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_format_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details={"validation_errors": clean_errors}
        ),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard HTTP exceptions (e.g. 404, 405)."""
    code = f"HTTP_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error_response(code=code, message=str(exc.detail)),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Fallback handler for unexpected exceptions.
    Logs error internally, but returns sanitized generic error to client.
    """
    logger.error(
        f"Unhandled exception during request: {type(exc).__name__}",
        exc_info=True,
        extra={"status_code": 500, "path": request.url.path}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_format_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred."
        ),
    )
