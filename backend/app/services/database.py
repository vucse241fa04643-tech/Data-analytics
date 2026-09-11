"""
Agent 63 – Safe Database Service Abstraction
Defines the architectural boundary and interface for future college PostgreSQL connectivity.

CRITICAL PHASE 2 ARCHITECTURAL BOUNDARY:
- Arbitrary SQL execution is strictly prohibited. There is NO `execute_arbitrary_sql()` method.
- No live PostgreSQL connection is initiated or required during Phase 2 startup.
- No local database, SQLite surrogate, or mock college records are created.
- The service inspects configuration status and reports connection readiness without executing queries.

Future Production Database Integration Principles:
- PostgreSQL 14+ required
- Dedicated read-only application role (e.g. `agent63_readonly`)
- Principle of Least Privilege: NO DDL, NO DML (INSERT/UPDATE/DELETE/ALTER/DROP)
- Connection timeout: 5 seconds max
- Statement timeout: 5000 milliseconds max
- SSL mode: require / verify-full in production
- All executed queries MUST be verified against the Phase 1 Schema Registry and RBAC permissions
"""

from typing import Any, Dict, Optional
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger("agent63.services.database")


class DatabaseStatus:
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    UNAVAILABLE = "unavailable"
    READY = "ready"


class CollegeDatabaseService:
    """
    Safe abstraction layer for future college PostgreSQL read-only interaction.
    Does NOT connect automatically or execute SQL in Phase 2.
    """

    def __init__(self):
        self._status: str = (
            DatabaseStatus.CONFIGURED if settings.is_database_configured else DatabaseStatus.NOT_CONFIGURED
        )

    def get_status(self) -> str:
        """Returns the current configuration/readiness status of the college database connection."""
        if not settings.is_database_configured:
            return DatabaseStatus.NOT_CONFIGURED
        return DatabaseStatus.CONFIGURED

    def get_status_message(self) -> str:
        """Returns human-readable, safe status without exposing database passwords."""
        if not settings.is_database_configured:
            return "College PostgreSQL connection is not configured."
        return f"College PostgreSQL configured for host '{settings.COLLEGE_DB_HOST}:{settings.COLLEGE_DB_PORT}' (connection deferred)."

    def get_safe_metadata(self) -> Dict[str, Any]:
        """Exposes safe non-secret configuration parameters."""
        return {
            "driver": settings.COLLEGE_DB_DRIVER,
            "host": settings.COLLEGE_DB_HOST if settings.COLLEGE_DB_HOST else None,
            "port": settings.COLLEGE_DB_PORT,
            "database": settings.COLLEGE_DB_NAME if settings.COLLEGE_DB_HOST else None,
            "ssl_mode": settings.COLLEGE_DB_SSL_MODE,
            "connect_timeout_sec": settings.COLLEGE_DB_CONNECT_TIMEOUT,
            "statement_timeout_ms": settings.COLLEGE_DB_STATEMENT_TIMEOUT,
            "configured": settings.is_database_configured,
        }

    async def check_connection(self) -> Dict[str, Any]:
        """
        Safe health/readiness probe.
        In Phase 2, this purely inspects environment readiness and explicitly avoids
        initiating network sockets or running queries against non-existent databases.
        """
        if not settings.is_database_configured:
            return {
                "status": DatabaseStatus.NOT_CONFIGURED,
                "detail": "College PostgreSQL connection is not configured.",
                "connected": False
            }

        # If credentials are provided in future phases, live connection probes will be handled here.
        return {
            "status": DatabaseStatus.CONFIGURED,
            "detail": "Credentials present; live socket probe deferred to subsequent phase.",
            "connected": False
        }


# Global database service instance
college_database_service = CollegeDatabaseService()
