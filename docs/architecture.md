# Agent 63 – Architecture Specification

> **Status:** Architectural Blueprint  
> **Phase 0 State:** Architecture Documented (Implementation Planned across Phases 1–16)

---

## 1. Architectural Philosophy & Principles
Agent 63 is engineered for enterprise-grade academic data intelligence. The fundamental thesis of this architecture is that **an LLM must never have direct, unmediated, or write access to an institutional database**.

Instead, natural-language reasoning is decoupled from database execution via a deterministic, multi-barrier pipeline:
1. **Semantic Decoupling:** User queries are resolved against approved business metrics before database logic is considered.
2. **Pre-Execution Authorization:** Role-based access control (RBAC) and row-level departmental scoping are injected prior to SQL construction.
3. **Deterministic SQL Generation:** Queries are derived from an immutable college schema registry and validated using Abstract Syntax Tree (AST) inspection.
4. **Least-Privilege Execution:** Read-only database connections with strict timeouts prevent mutation and long-running locks.
5. **Post-Execution Result Verification:** All query outputs undergo type, boundary, and mathematical sanity checks before presentation.

---

## 2. End-to-End Conceptual Flow

```
USER (Institutional Stakeholder)
  │
  ▼
[1] AGENT 63 INSTITUTIONAL UI (React + Vite, Institutional Design System)
  │
  ▼
[2] FASTAPI BACKEND GATEWAY (REST / WebSocket API)
  │
  ▼
[3] AUTHENTICATION SERVICE (JWT / Session Verification)
  │
  ▼
[4] RBAC & DATA SCOPE ENGINE (Role & Department Authorization Boundary)
  │
  ▼
[5] AGENT 63 ORCHESTRATOR (Context & Pipeline State Machine)
  │
  ▼
[6] SEMANTIC LAYER & METRIC CATALOG (Formulas, Dimensions, Aggregations)
  │
  ▼
[7] STRUCTURED INTENT PARSER (Pydantic Intent Object Extraction)
  │
  ▼
[8] AUTHORIZED DATA SCOPE FILTER (Department, Program, Cohort Injection)
  │
  ▼
[9] COLLEGE DATABASE SCHEMA REGISTRY (Inspected Real Database Tables & Columns)
  │
  ▼
[10] SAFE SQL GENERATION (Read-Only Parameterized SQL Builder)
  │
  ▼
[11] SQL VALIDATOR (AST Parser: Forbids INSERT/UPDATE/DELETE/ALTER/DROP)
  │
  ▼
[12] READ-ONLY QUERY EXECUTOR (Isolated Read-Only DB Connection Pool)
  │
  ▼
[13] COLLEGE-PROVIDED DATABASE(S) (Authoritative Institutional Records)
  │
  ▼
[14] RESULT VALIDATOR (Boundary, Data Type, Null & Sanity Verification)
  │
  ▼
[15] ANALYTICS & ANOMALY ENGINE (Baselines, Trends, Deviations)
  │
  ▼
[16] VISUALIZATION ENGINE (Recharts Schema Generator)
  │
  ▼
[17] EXPLANATION & METADATA BUILDER (Context, Assumptions, Verification Tag)
  │
  ▼
[18] VERIFIED RESULT CARD (Rendered on Institutional UI)
  │
  ▼
USER
```

---

## 3. Component Deep Dive

### Current Architecture Pipeline Status (Phases 0–7 Complete)

```
Frontend [IMPLEMENTED - Phase 3]
   ↓
FastAPI Backend Gateway [IMPLEMENTED - Phase 2]
   ↓
Authentication & Token Verification [IMPLEMENTED - Phase 5]
   ↓
RBAC & Data Scoping Engine [IMPLEMENTED - Phase 5]
   ↓
Semantic Layer & Metric Catalog [IMPLEMENTED - Phase 4]
   ↓
Schema Registry Service [IMPLEMENTED - Phase 1 & 2]
   ↓
Structured Intent Parser (Groq API) [IMPLEMENTED - Phase 6]
   ↓
Safe SQL Generator (Parameter Separation & Role Scoping) [IMPLEMENTED - Phase 7]
   ↓
SQL AST Validator (sqlglot PostgreSQL Dialect) [IMPLEMENTED - Phase 7]
   ↓
[Future Read-Only College DB Execution Pool - Phase 8+]
```


### [1] Institutional UI & Branding Layer
- **Status:** IMPLEMENTED (*Phase 3*)
- **Responsibility:** Deliver a responsive, desktop-first analytics workspace reflecting the college's visual design family (white surfaces, light blue backgrounds, dark navy typography, rounded cards, institutional header, and accreditation logos).
- **Inputs:** User natural language prompts, filter interactions, dashboard requests.
- **Outputs:** Visual rendered result cards, Recharts visualizations, system state alerts.
- **Security Boundary:** Client-side only. Does not enforce security; treats backend as authoritative.
- **Dependencies:** React 18+, Vite, TypeScript, React Router, Centralized CSS Tokens.

### [2] FastAPI Backend Gateway & Core Services
- **Status:** IMPLEMENTED (*Phase 2*)
- **Responsibility:** Serves as the secure foundational API gateway, providing modular routing (`/api/v1`), request correlation IDs (`X-Request-ID`), structured logging with credential scrubbing, centralized error sanitization, CORS restriction, schema registry in-memory service, and safe database abstraction.
- **Inputs:** HTTP JSON requests.
- **Outputs:** Sanitized JSON API responses with correlation tracking.
- **Security Boundary:** First backend perimeter. Strips unsafe inputs and sanitizes error payloads.
- **Dependencies:** FastAPI, Uvicorn, Pydantic v2, Python 3.14+.

### [3] Authentication Service
- **Status:** IMPLEMENTED (*Phase 5*)
- **Responsibility:** Authenticate institutional users via Argon2id password verification, issue cryptographically signed JWT bearer tokens with standard claims (`sub`, `jti`, `exp`, `nbf`, `iss`, `aud`), support server-side token revocation abstraction via JTI tracking, and resolve authentic server-side principal identities without trusting client-supplied role claims.
- **Inputs:** Credentials from API login request (`POST /api/v1/auth/login`).
- **Outputs:** Signed access token and verified `AuthenticatedPrincipal` identity.
- **Security Boundary:** First authentication perimeter. Enforces constant-time hash verification, token expiry, algorithm pinning, JTI revocation checks, and secret scrubbing.
- **Dependencies:** `PyJWT`, `argon2-cffi`, `AuthenticationService`, `TokenRevocationStore`.

### [4] Role-Based Access Control (RBAC) & Scoping Engine
- **Status:** IMPLEMENTED (*Phase 5*)
- **Responsibility:** Evaluate user roles (`STUDENT`, `FACULTY`, `MENTOR`, `HOD`, `DEAN`, `COE`, `IQAC`, `PLACEMENT`, `ACCOUNTS`, `COUNSELLOR`, `PRINCIPAL`, `ADMIN`) against requested permissions, organizational scopes (`SELF`, `SECTION`, `COURSE_OFFERING`, `PROGRAMME`, `DEPARTMENT`, `CAMPUS`, `INSTITUTION`), and Phase 4 semantic metric sensitivity tiers (`PUBLIC_ANALYTICS`, `INTERNAL_ANALYTICS`, `ROLE_RESTRICTED`, `SENSITIVE`, `HIGHLY_SENSITIVE`).
- **Inputs:** Authenticated principal, requested metric ID or domain action, organizational scope parameters.
- **Outputs:** Deterministic authorization decisions (`ALLOW` or `DENY` with audit logging), and mandatory scoping filters.
- **Security Boundary:** Critical authorization barrier. Enforced in Python backend code; client role headers and JWT role claims are never trusted; cannot be overridden by user prompts or LLM output.
- **Dependencies:** `AuthorizationService`, `IdentityRepository`, `SemanticRegistryService`.

### [5] Agent 63 Orchestrator
- **Status:** PLANNED (*Phase 6*)
- **Responsibility:** Coordinates pipeline execution, manages conversational state, resolves follow-up questions, and handles error fallbacks.
- **Inputs:** User query string, conversation history, user scope context.
- **Outputs:** Orchestrated pipeline stages from intent to final presentation.
- **Security Boundary:** Isolates the LLM from database execution tools.
- **Dependencies:** FastAPI backend service layer.

### [6] Semantic Layer & Metric Catalog
- **Status:** IMPLEMENTED (*Phase 4*)
- **Responsibility:** Single authoritative source of truth for institutional metric definitions, mathematical formulas, aggregation rules, dimensions, controlled foreign-key join paths, and null handling.
- **Inputs:** Metric identifiers requested by intent parser or backend services.
- **Outputs:** Formal machine-readable metric specifications (source tables, verified join paths, formulas, allowed dimensions, sensitivity tiers).
- **Security Boundary:** Eliminates metric hallucination; the LLM is strictly prohibited from inventing formulas or joins. Excludes `confidential.*` and enforces placement fairness.
- **Dependencies:** `semantic_layer/registry/semantic_registry.json`, `backend/app/services/semantic_registry.py`, `scripts/validate_semantic_layer.py`.

### [7] Structured Intent Parser
- **Status:** IMPLEMENTED (*Phase 6*)
- **Responsibility:** Translates unstructured natural language into a strictly typed, validated `StructuredIntent` object using Google Gemini (`google-genai` SDK) grounded exclusively in the Phase 4 Semantic Layer.
- **Inputs:** Natural language question from authenticated user, prompt compiled from approved Phase 4 metrics and dimensions.
- **Outputs:** Validated, authorized `StructuredIntent` (Intent Type, Primary Metric, Secondary Metrics, Dimensions, Filters, Time Context, Reasoning Summary).
- **Security Boundary:** Strict JSON schema enforcement, zero SQL generation, deterministic `IntentValidator` catalog checks, and server-side `AuthorizationService` scoping evaluation.
- **Dependencies:** Google GenAI SDK (`google-genai`), Pydantic v2, `IntentValidator`, `AuthorizationService`, `SemanticRegistryService`.

### [8] Authorized Data Scope Filter
- **Status:** PLANNED (*Phase 5/7*)
- **Responsibility:** Merges user intent with mandatory RBAC filters. For example, if an HOD asks "Show all attendance", this layer forces `department = 'CSE'`.
- **Inputs:** Raw intent schema, user scope constraints.
- **Outputs:** Scoped intent schema.
- **Security Boundary:** Non-negotiable query containment.
- **Dependencies:** RBAC service.

### [9] College Database Schema Registry
- **Status:** IMPLEMENTED / PHASE 1 PREPARED (`database/mappings/agent63_schema_registry.json`)
- **Responsibility:** Controlled, read-only representation of the actual college-provided PostgreSQL 14+ database (21 schemas, 225 tables, 11 views, 7 RLS-enabled tables).
- **Inputs:** Inspected physical schema (`01_foundation.sql` / `schema_full.sql`).
- **Outputs:** Machine-readable Schema Registry (`agent63_schema_registry.json`) and inventory (`college_schema_inventory.json`).
- **Security Boundary:** Restricts queryable scope to approved institutional objects; enforces strict `DENY_GENERAL_ANALYTICS` on `confidential.*` and exam security tables.
- **Dependencies:** Schema inspection parser and registry validator (`scripts/validate_schema_registry.py`).

### [10] Safe SQL Generator
- **Status:** IMPLEMENTED (*Phase 7*)
- **Responsibility:** Deterministically constructs parameterized, read-only PostgreSQL SELECT queries combining the validated StructuredIntent, Semantic Layer metric definitions, and Schema Registry objects.
- **Inputs:** Validated `StructuredIntent`, `AuthenticatedPrincipal`, metric definitions from Semantic Layer.
- **Outputs:** Parameterized `SQLArtifact` with bound values in `parameters: Dict[str, Any]`, separated from SQL text.
- **Security Boundary:** Zero user input interpolation. Enforces server-side authorization scoping predicates (e.g. STUDENT self-scope, HOD departmental scope).
- **Dependencies:** `SQLCompiler`, `SemanticRegistryService`, `SchemaRegistryService`, `AuthorizationService`.

### [11] SQL Validator
- **Status:** IMPLEMENTED (*Phase 7*)
- **Responsibility:** Performs Abstract Syntax Tree (AST) inspection of every compiled SQL statement using `sqlglot` (PostgreSQL dialect) before returning artifacts.
- **Inputs:** Parameterized `SQLArtifact`.
- **Outputs:** Verified `SQLArtifact` with `validation_status = "VALID"`, or raises `SQLValidationError`.
- **Security Boundary:** Multi-tier AST defense: single statement, `exp.Select` only, no `SELECT *`, no SQL comments, strict schema/table/function allowlists, confidential quarantine, mandatory limit bounds (`1 <= limit <= 1000`).
- **Dependencies:** `sqlglot`, `SQLValidator`, `SchemaRegistryService`.


### [12] Read-Only Query Executor
- **Status:** IMPLEMENTED (*Phase 8*)
- **Responsibility:** Connects to the college PostgreSQL database using strictly read-only transactions, parameter translation (:param to %(param)s), statement timeouts (default 5000ms), and row/byte limits (max 1000 rows, 1MB).
- **Inputs:** Validated SQLArtifact and parameters.
- **Outputs:** Raw tabular query result set, column types, and execution timing.
- **Security Boundary:** Database session-level read-only mode (`SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;`), driver timeout enforcement, and fail-closed handling when database is unconfigured.
- **Dependencies:** `psycopg[binary]>=3.1.0`.

### [13] College-Provided Database(s)
- **Status:** Authoritative Institutional Source (*Inspected in Phase 1*)
- **Responsibility:** Stores official institutional operational and academic data.
- **Inputs:** Read-only `SELECT` queries.
- **Outputs:** Authoritative institutional records.
- **Security Boundary:** Physically and logically isolated. Write access is strictly prohibited.
- **Dependencies:** College IT infrastructure.

### [14] Result Validator
- **Status:** IMPLEMENTED (*Phase 8*)
- **Responsibility:** Validates result integrity: checks expected columns, validates row counts, handles empty result sets, normalizes Decimals to floats and dates to ISO-8601, preserves NULLs, rejects NaN/Infinity values, and enforces domain physical bounds (percentages in [0, 100], counts >= 0, scales in [0, 3]).
- **Inputs:** Tabular database result set, metric metadata, and execution timing.
- **Outputs:** Safe normalized `QueryResult` model.
- **Security Boundary:** Prevents presentation of corrupt, impossible, or hallucinated numbers.
- **Dependencies:** Pydantic models, `math` IEEE-754 validation.

### [15] Analytics & Anomaly Engine
- **Status:** PLANNED (*Phase 11*)
- **Responsibility:** Computes statistical baselines, historical standard deviations, percentage changes, and flags anomalies.
- **Inputs:** Validated historical datasets.
- **Outputs:** Anomaly alerts, trend flags, statistical context.
- **Security Boundary:** Transparent mathematical logic; never fabricates causes.
- **Dependencies:** NumPy / SciPy / pure Python statistical functions.

### [16] Visualization Engine
- **Status:** PLANNED (*Phase 9*)
- **Responsibility:** Selects appropriate chart types (bar, line, KPI card, distribution) and outputs standard JSON specifications for Recharts.
- **Inputs:** Validated dataset, metric dimensionality.
- **Outputs:** Standardized chart configuration schema (data, series, colors, axes).
- **Security Boundary:** Generates data specifications, never executable JavaScript.
- **Dependencies:** Visualization mapper.

### [17] Explanation & Metadata Builder
- **Status:** PLANNED (*Phase 9*)
- **Responsibility:** Generates human-readable explanations summarizing the metric definition, population, applied filters, assumptions, and official verification status.
- **Inputs:** Metric metadata, intent context, query execution statistics.
- **Outputs:** Structured explanation block for the UI result card.
- **Security Boundary:** Contextual audit trail for full transparency.
- **Dependencies:** Internal explanation formatter.

---

## 4. Institutional Database Integrity Guarantee
- **No Synthetic Databases:** The college-provided database is the sole data source for institutional analytics.
- **No Schema Assumptions:** The system makes no premature assumptions regarding whether the database uses PostgreSQL, MySQL, SQL Server, or Oracle until Phase 1 inspection is complete.
- **No Schema Mutations:** The Agent 63 platform will never perform `CREATE`, `ALTER`, `DROP`, `INSERT`, `UPDATE`, or `DELETE` on the college database.
