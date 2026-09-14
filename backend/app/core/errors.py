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


class RegistrationError(AppException):
    """Raised when institutional self-registration or account creation fails validation."""
    def __init__(self, message: str = "Registration failed.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="REGISTRATION_FAILED",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
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


class GroqError(AppException):
    """Raised when Groq provider returns an operational, rate-limiting, or network failure."""
    def __init__(self, message: str = "Groq intent service failure.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GROQ_ERROR",
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class GroqConfigurationError(AppException):
    """Raised when Groq API key or configuration is missing when invoked."""
    def __init__(self, message: str = "Groq API is not configured on this server.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GROQ_NOT_CONFIGURED",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class GroqTimeoutError(AppException):
    """Raised when Groq API call exceeds configured timeout bounds."""
    def __init__(self, message: str = "Groq intent extraction timed out.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GROQ_TIMEOUT",
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details,
        )


class GeminiError(AppException):
    """Raised when Google Gemini provider returns an operational or network failure."""
    def __init__(self, message: str = "Google Gemini intent service failure.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GEMINI_ERROR",
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class GeminiConfigurationError(AppException):
    """Raised when Google Gemini API key or configuration is missing when invoked."""
    def __init__(self, message: str = "Google Gemini API is not configured on this server.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GEMINI_NOT_CONFIGURED",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class GeminiTimeoutError(AppException):
    """Raised when Google Gemini API call exceeds configured timeout bounds."""
    def __init__(self, message: str = "Google Gemini intent extraction timed out.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="GEMINI_TIMEOUT",
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details,
        )


class IntentValidationError(AppException):
    """Raised when extracted intent violates semantic layer catalog or security policy."""
    def __init__(self, message: str = "Structured intent validation failed.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="INTENT_VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class SQLCompilationError(AppException):
    """Raised when structured intent cannot be safely compiled into an institutional SQL artifact."""
    def __init__(self, message: str = "SQL compilation failed.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SQL_COMPILATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class SQLValidationError(AppException):
    """Raised when generated SQL fails AST-level security or structural validation rules."""
    def __init__(self, message: str = "Generated SQL failed safety validation.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SQL_VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class SQLAuthorizationError(AppException):
    """Raised when user authorization scope cannot safely support requested SQL query compilation."""
    def __init__(self, message: str = "Access denied: insufficient scope for requested analytical query.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SQL_AUTHORIZATION_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


# =========================================================================
# Phase 8: Safe SQL Execution & Result Validation Exceptions
# =========================================================================

class DatabaseNotConfiguredError(AppException):
    """Raised when query execution is attempted but college database credentials/host are missing."""
    def __init__(self, message: str = "Institutional PostgreSQL database connection is not configured.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="DATABASE_NOT_CONFIGURED",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class DatabaseConnectionError(AppException):
    """Raised when backend fails to establish connection to PostgreSQL."""
    def __init__(self, message: str = "Failed to establish connection to institutional database.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="DATABASE_CONNECTION_ERROR",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class DatabaseTimeoutError(AppException):
    """Raised when query execution exceeds the configured statement timeout."""
    def __init__(self, message: str = "Database query execution exceeded configured statement timeout.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="DATABASE_TIMEOUT",
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details,
        )


class DatabaseExecutionError(AppException):
    """Raised when database query execution fails with a PostgreSQL operational or driver error."""
    def __init__(self, message: str = "An error occurred during safe database query execution.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="DATABASE_EXECUTION_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ResultValidationError(AppException):
    """Raised when raw database query results fail mathematical, type, or integrity checks."""
    def __init__(self, message: str = "Query result validation failed against semantic catalog rules.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RESULT_VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details,
        )


class ResultSizeLimitExceededError(AppException):
    """Raised when database result row count or payload size exceeds configured bounds."""
    def __init__(self, message: str = "Query result exceeds maximum permitted row count or response size.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RESULT_SIZE_EXCEEDED",
            message=message,
            status_code=413,
            details=details,
        )


class SecurityValidationError(AppException):
    """Raised when an artifact fails pre-execution defense-in-depth security checks."""
    def __init__(self, message: str = "Security validation failed prior to execution.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SECURITY_VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
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
