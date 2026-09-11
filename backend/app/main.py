"""
Agent 63 – FastAPI Application Entrypoint
Establishes the secure backend foundation for Agent 63.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from backend.app.core.logging import get_logger, setup_logging
from backend.app.core.middleware import RequestCorrelationMiddleware
from backend.app.services.schema_registry import schema_registry_service

# Initialize structured logging foundation
setup_logging(settings.LOG_LEVEL)
logger = get_logger("agent63.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle management.
    Initializes internal service state without requiring live database connections.
    """
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [env: {settings.APP_ENV}]"
    )

    # Validate schema registry availability at startup (soft check; logged, does not crash)
    try:
        if schema_registry_service.is_ready:
            count = schema_registry_service.get_object_count()
            logger.info(f"Schema Registry verified successfully ({count} objects indexed).")
        else:
            logger.warning("Schema Registry could not be loaded at startup.")
    except Exception as e:
        logger.warning(f"Schema Registry pre-flight check notice: {str(e)}")

    # Database connectivity notice
    if not settings.is_database_configured:
        logger.info("College PostgreSQL connectivity: unconfigured (Phase 2 operational default).")
    else:
        logger.info(f"College PostgreSQL parameters detected for host '{settings.COLLEGE_DB_HOST}'.")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


def create_application() -> FastAPI:
    """Application factory providing a configured FastAPI instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Secure Institutional Data Analytics Agent - Backend Foundation",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    # 1. Request Correlation ID & Access Logging Middleware
    app.add_middleware(RequestCorrelationMiddleware)

    # 2. CORS Middleware (Environment-configured origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # 3. Centralized Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Mount API Routes
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_application()
