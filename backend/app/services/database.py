"""
Agent 63 - Safe Database Service Abstraction
Defines the architectural boundary and interface for college PostgreSQL connectivity.

PHASE 8 ARCHITECTURAL BOUNDARIES:
- Read-only execution exclusively. All sessions enforce read-only transactions.
- Parameterized execution exclusively: no string concatenation or query interpolation.
- Safe parameter translation from SQLArtifact :param syntax to driver-native %(param)s syntax.
- Enforced statement timeouts and result row/byte limits.
- If unconfigured, fails closed with DatabaseNotConfiguredError without attempting network calls.
- Absolute secret hygiene: zero credentials logged, printed, or exposed in errors.
"""

from __future__ import annotations

import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row

from backend.app.core.config import settings
from backend.app.core.errors import (
    DatabaseConnectionError,
    DatabaseExecutionError,
    DatabaseNotConfiguredError,
    DatabaseTimeoutError,
    ResultSizeLimitExceededError,
)
from backend.app.core.logging import get_logger

logger = get_logger("agent63.services.database")


class DatabaseStatus:
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    UNAVAILABLE = "unavailable"
    READY = "ready"


def translate_named_parameters(sql: str) -> str:
    """
    Translates SQLArtifact named parameters (:param) to psycopg named parameters (%(param)s).
    Preserves PostgreSQL type casts like ::text or ::integer by using negative lookbehind and lookahead.
    """
    # Matches :identifier when not preceded by : (typecast) and ensures complete word matching
    pattern = re.compile(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)(?![a-zA-Z0-9_])")
    return pattern.sub(r"%(\1)s", sql)


class CollegeDatabaseService:
    """
    Safe abstraction layer for college PostgreSQL read-only interaction.
    Enforces read-only transactions, parameter safety, timeouts, and result limits.
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
        return (
            f"College PostgreSQL configured for host '{settings.COLLEGE_DB_HOST}:{settings.COLLEGE_DB_PORT}'."
        )

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
            "min_pool_size": settings.COLLEGE_DB_MIN_POOL_SIZE,
            "max_pool_size": settings.COLLEGE_DB_MAX_POOL_SIZE,
            "max_result_rows": settings.MAX_RESULT_ROWS,
            "max_result_bytes": settings.MAX_RESULT_BYTES,
            "configured": settings.is_database_configured,
        }

    def _get_connection_kwargs(self) -> Dict[str, Any]:
        """Constructs connection keyword arguments from settings."""
        if not settings.is_database_configured:
            raise DatabaseNotConfiguredError("Institutional database connection is not configured.")

        kwargs: Dict[str, Any] = {
            "host": settings.COLLEGE_DB_HOST,
            "port": settings.COLLEGE_DB_PORT,
            "dbname": settings.COLLEGE_DB_NAME,
            "user": settings.COLLEGE_DB_USER,
            "password": settings.COLLEGE_DB_PASSWORD,
            "connect_timeout": settings.COLLEGE_DB_CONNECT_TIMEOUT,
            "row_factory": dict_row,
        }
        if settings.COLLEGE_DB_SSL_MODE:
            kwargs["sslmode"] = settings.COLLEGE_DB_SSL_MODE

        return kwargs

    async def check_connection(self) -> Dict[str, Any]:
        """
        Safe health/readiness probe.
        If configured, attempts a lightweight read-only query.
        """
        if not settings.is_database_configured:
            return {
                "status": DatabaseStatus.NOT_CONFIGURED,
                "detail": "College PostgreSQL connection is not configured.",
                "connected": False,
            }

        try:
            conn_kwargs = self._get_connection_kwargs()
            # Execute quick test probe
            with psycopg.connect(**conn_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
                    cur.execute("SELECT 1 AS probe;")
                    row = cur.fetchone()
                    if row and row.get("probe") == 1:
                        return {
                            "status": DatabaseStatus.READY,
                            "detail": "Connection healthy and verified read-only.",
                            "connected": True,
                        }
            return {
                "status": DatabaseStatus.UNAVAILABLE,
                "detail": "Connection probe failed to return expected result.",
                "connected": False,
            }
        except psycopg.OperationalError as exc:
            logger.warning("Database connection probe failed: %s", str(exc).split("\n")[0])
            return {
                "status": DatabaseStatus.UNAVAILABLE,
                "detail": "Database connection failed.",
                "connected": False,
            }
        except Exception as exc:
            logger.error("Unexpected error during database probe: %s", str(exc).split("\n")[0])
            return {
                "status": DatabaseStatus.UNAVAILABLE,
                "detail": "Database health check encountered an error.",
                "connected": False,
            }

    def execute_query(
        self,
        sql: str,
        parameters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        statement_timeout_ms: Optional[int] = None,
    ) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, str], float]:
        """
        Executes a validated read-only SQL query with parameters, statement timeout, and result limits.

        Returns:
            Tuple of:
            - columns: List[str]
            - rows: List[Dict[str, Any]]
            - data_types: Dict[str, str] (column name -> PostgreSQL type name / description)
            - execution_time_ms: float
        """
        if not settings.is_database_configured:
            raise DatabaseNotConfiguredError(
                "Institutional database connection is not configured. Execution aborted."
            )

        timeout = statement_timeout_ms or settings.COLLEGE_DB_STATEMENT_TIMEOUT
        max_rows = min(limit or settings.MAX_RESULT_ROWS, settings.MAX_RESULT_ROWS)
        effective_params = parameters or {}

        # Translate named parameters from :name to %(name)s
        native_sql = translate_named_parameters(sql)

        conn_kwargs = self._get_connection_kwargs()
        start_time = time.perf_counter()

        try:
            with psycopg.connect(**conn_kwargs) as conn:
                # Force read-only transaction mode
                conn.read_only = True
                with conn.cursor() as cur:
                    # Explicit session-level guard against any state change
                    cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
                    # Set PostgreSQL statement timeout
                    cur.execute(f"SET statement_timeout = {int(timeout)};")

                    # Execute parameterized query
                    cur.execute(native_sql, effective_params)

                    # Extract column names and types from cursor description
                    columns: List[str] = []
                    data_types: Dict[str, str] = {}
                    if cur.description:
                        for col in cur.description:
                            col_name = str(col.name)
                            columns.append(col_name)
                            # Type code / name representation
                            data_types[col_name] = str(col.type_display) if hasattr(col, "type_display") else "unknown"

                    # Fetch rows up to max_rows + 1 to detect limit breaches
                    raw_rows = cur.fetchmany(max_rows + 1)
                    if len(raw_rows) > max_rows:
                        # Row limit exceeded
                        raise ResultSizeLimitExceededError(
                            f"Result set exceeded maximum permitted limit of {max_rows} rows."
                        )

                    # Check byte size limit
                    total_bytes = sys.getsizeof(raw_rows)
                    for r in raw_rows:
                        total_bytes += sys.getsizeof(r)
                    if total_bytes > settings.MAX_RESULT_BYTES:
                        raise ResultSizeLimitExceededError(
                            f"Result payload size ({total_bytes} bytes) exceeds limit ({settings.MAX_RESULT_BYTES} bytes)."
                        )

                    execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return columns, raw_rows, data_types, execution_time_ms

        except psycopg.errors.QueryCanceled as exc:
            logger.warning("Query execution timed out after %d ms", timeout)
            raise DatabaseTimeoutError(
                f"Query execution timed out after {timeout} ms."
            ) from exc
        except psycopg.errors.ReadOnlySqlTransaction as exc:
            logger.error("Attempted non-read-only operation in read-only transaction: %s", exc)
            raise DatabaseExecutionError(
                "Execution aborted: write operations are strictly prohibited."
            ) from exc
        except psycopg.OperationalError as exc:
            logger.error("PostgreSQL operational/connection error: %s", str(exc).split("\n")[0])
            raise DatabaseConnectionError(
                "Failed to connect to institutional database or connection interrupted."
            ) from exc
        except psycopg.Error as exc:
            logger.error("PostgreSQL query execution error: %s", str(exc).split("\n")[0])
            raise DatabaseExecutionError(
                f"Database query execution failed: {str(exc).splitlines()[0]}"
            ) from exc


# Global database service instance
college_database_service = CollegeDatabaseService()
