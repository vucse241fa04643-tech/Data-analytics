"""
Agent 63 – Middleware Foundation
Implements request correlation IDs (X-Request-ID) and structured request logging with timing.
"""

import re
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.logging import get_logger, request_id_ctx_var

logger = get_logger("agent63.access")

# Allowed characters for inbound correlation ID: alphanumeric and hyphens, 8-64 chars
VALID_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that establishes a correlation ID for every inbound HTTP request.
    Validates client-supplied X-Request-ID header or generates a cryptographically random UUIDv4.
    Injects the ID into the logging context and attaches it to response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inbound_id = request.headers.get("X-Request-ID")
        
        # Validate format of inbound correlation ID to prevent header injection or tracking leaks
        if inbound_id and VALID_REQUEST_ID_REGEX.match(inbound_id):
            request_id = inbound_id
        else:
            request_id = str(uuid.uuid4())

        # Set context variable for structured logging
        token = request_id_ctx_var.set(request_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Attach X-Request-ID to outgoing response headers
            response.headers["X-Request-ID"] = request_id

            # Log request completion with timing
            logger.info(
                f"{request.method} {request.url.path} returned {response.status_code} in {duration_ms}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                }
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"{request.method} {request.url.path} failed after {duration_ms}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
            raise
        finally:
            request_id_ctx_var.reset(token)
