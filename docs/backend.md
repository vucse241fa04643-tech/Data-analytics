# Agent 63 – Backend Architecture & Implementation Guide (Phase 2)

## 1. Overview

Agent 63's backend is implemented using **FastAPI** (Python 3.10+ / 3.14 compatible), providing an enterprise-grade, secure, modular foundation for conversational institutional data analytics.

> [!IMPORTANT]
> **Phase 2 does not require a live PostgreSQL database.**
> College PostgreSQL connectivity remains unconfigured until an actual populated college database and authorized read-only credentials are provided. Missing database credentials do not prevent application startup or health check verification.

---

## 2. Architecture & Service Boundaries

```text
HTTP Request
     ↓
[RequestCorrelationMiddleware]   (Generates / validates X-Request-ID; logs latency)
     ↓
[CORSMiddleware]                 (Restricted to configured institutional origins)
     ↓
[Centralized Exception Handlers] (Sanitized JSON errors; no stack traces or path leaks)
     ↓
[API Routers: /api/v1/...]       (Modular route namespaces)
     ├── /health                 (Service liveness probe; always ok if app running)
     └── /health/ready           (Dependency readiness probe: schema registry & DB status)
     ↓
[Application Services]
     ├── SchemaRegistryService   (Consumes Phase 1 agent63_schema_registry.json)
     └── CollegeDatabaseService  (Abstract boundary; unconfigured in Phase 2, no SQL execution)
```

---

## 3. Directory Layout

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, middleware, lifespan
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py               # Top-level API router mounting /v1
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # API v1 aggregator
│   │       └── health.py           # Liveness and readiness route handlers
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings & environment variable loader
│   │   ├── logging.py              # Structured JSON logging & secret scrubbing
│   │   ├── errors.py               # Centralized exception hierarchy & handlers
│   │   ├── middleware.py           # Correlation ID & request timing middleware
│   │   └── security.py             # Abstract principal, role & decision definitions
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py               # BaseResponse, ErrorDetail, ErrorResponse
│   │   └── health.py               # HealthResponse, ReadinessResponse
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── schema_registry.py      # Authoritative Phase 1 registry service
│   │   └── database.py             # Safe college PostgreSQL service abstraction
│   │
│   └── dependencies/
│       ├── __init__.py
│       └── common.py               # Dependency injection providers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures and test client setup
│   ├── test_app_init.py            # App initialization and settings tests
│   ├── test_database_service.py    # Safe database layer isolation tests
│   ├── test_error_handling.py      # Error structure and trace leakage tests
│   ├── test_health_endpoints.py    # /health and /health/ready probe tests
│   ├── test_request_correlation.py # X-Request-ID validation & generation tests
│   ├── test_schema_registry_service.py # Phase 1 mapping loading & lookups
│   └── test_security_boundaries.py # Audit asserting absence of arbitrary SQL
│
├── requirements.txt                # Backend dependencies (fastapi, uvicorn, pydantic, etc.)
└── README.md                       # Local development startup instructions
```

---

## 4. Configuration Management

Configuration is loaded through `pydantic-settings` via `backend.app.core.config.Settings`.

### Environment Variables Supported:

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_NAME` | string | `Agent 63 Institutional Analytics Backend` | Human-readable service name |
| `APP_VERSION` | string | `0.1.0` | Semantic version |
| `APP_ENV` | string | `development` | Environment (`development`, `production`) |
| `APP_DEBUG` | boolean | `false` | Debug mode |
| `API_PREFIX` | string | `/api` | Base API prefix |
| `API_V1_STR` | string | `/api/v1` | Version 1 API prefix |
| `HOST` | string | `0.0.0.0` | Server bind host |
| `PORT` | integer | `8000` | Server bind port |
| `CORS_ORIGINS` | JSON list | `["http://localhost:5173"]` | Allowed CORS origins |
| `LOG_LEVEL` | string | `INFO` | Root logging level |
| `COLLEGE_DB_DRIVER` | string | `postgresql` | Database driver protocol |
| `COLLEGE_DB_HOST` | string | `None` | College PostgreSQL host |
| `COLLEGE_DB_PORT` | integer | `5432` | PostgreSQL port |
| `COLLEGE_DB_NAME` | string | `academic_agent_platform` | Target database name |
| `COLLEGE_DB_USER` | string | `None` | Read-only database user |
| `COLLEGE_DB_PASSWORD` | string | `None` | Read-only password |
| `COLLEGE_DB_SSL_MODE` | string | `prefer` | SSL negotiation mode |
| `COLLEGE_DB_CONNECT_TIMEOUT` | integer | `5` | Connection timeout in seconds |
| `COLLEGE_DB_STATEMENT_TIMEOUT` | integer | `5000` | Statement timeout in ms |
| `SCHEMA_REGISTRY_PATH` | string | `None` | Optional override for registry path |

> [!NOTE]
> Database variables are strictly optional in Phase 2. If `COLLEGE_DB_HOST` or `COLLEGE_DB_USER` are not set, the backend initializes cleanly and marks `college_database` as `not_configured`.

---

## 5. API Endpoints

### 5.1 Service Liveness Probe
- **Method:** `GET`
- **Path:** `/api/v1/health`
- **Description:** Always returns `200 OK` with service metadata if the backend process is running.
- **Example Response:**
  ```json
  {
    "status": "ok",
    "service": "agent63-backend",
    "version": "0.1.0"
  }
  ```

### 5.2 Dependency Readiness Probe
- **Method:** `GET`
- **Path:** `/api/v1/health/ready`
- **Description:** Evaluates backend dependencies without executing arbitrary SQL. Explicitly reports the difference between operational schema metadata and unconfigured database connectivity.
- **Example Response (Phase 2 Default):**
  ```json
  {
    "status": "degraded",
    "service": "agent63-backend",
    "version": "0.1.0",
    "dependencies": {
      "schema_registry": "ready",
      "college_database": "not_configured",
      "schema_registry_objects": 236,
      "database_host": null
    }
  }
  ```

---

## 6. Correlation IDs & Structured Logging

1. **Correlation IDs (`X-Request-ID`):**
   - Inbound `X-Request-ID` headers are validated against `^[a-zA-Z0-9_-]{8,64}$`.
   - Invalid, dangerous, or missing IDs are replaced with fresh `uuid.uuid4()`.
   - Attached to the response header `X-Request-ID`.
   - Propagated to all log records emitted during that request lifecycle via Python `contextvars`.

2. **Structured JSON Logging:**
   - Emits standardized JSON logs to `sys.stdout`.
   - Automatically sanitizes sensitive keys (`password`, `secret`, `token`, `authorization`, `counselling`).
   - Request bodies are NOT logged.
   - Stack traces are retained internally in logs but NEVER returned to API clients.

---

## 7. Error Handling

All HTTP errors and unhandled exceptions return a standardized error envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "details": {}
  }
}
```

Internal exception classes:
- `AppException` (base)
- `ResourceNotFoundError` (HTTP 404)
- `ConfigurationError` (HTTP 500)
- `SchemaRegistryError` (HTTP 500)
- `ServiceUnavailableError` (HTTP 503)

---

## 8. Schema Registry Integration

- Consumes `database/mappings/agent63_schema_registry.json` as the sole source of truth.
- Validates 236 registered database objects across 21 institutional schemas.
- In-memory O(1) indexed lookup via `schema_registry_service.get_object("core.institution")`.
- Strictly internal to backend services; no public discovery endpoint (`GET /api/v1/schema`) is exposed.

---

## 9. Security Boundaries Enforced

1. **No Arbitrary SQL Execution:** No endpoint exists or will ever exist that accepts raw SQL from clients (e.g. `/execute-sql`, `/query`).
2. **No Public Registry Exposure:** Schema registry is an internal backend knowledge store, not exposed over unauthenticated public endpoints.
3. **No Auth Bypass:** No mock logins, hard-coded admin passwords, or test bypasses exist.
4. **No Credential Leakage:** Database credentials and tokens are scrubbed from logs and error responses.
