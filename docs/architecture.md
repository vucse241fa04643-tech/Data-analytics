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

### Phase 3 Architecture Pipeline Status

```
Frontend [IMPLEMENTED - Phase 3]
   ↓
FastAPI Backend [IMPLEMENTED - Phase 2]
   ↓
API Router [IMPLEMENTED - Phase 2]
   ↓
Application Services [IMPLEMENTED - Phase 2]
   ↓
[Future Authentication / RBAC - Phase 4/5]
   ↓
[Future Semantic Layer - Phase 6]
   ↓
Schema Registry Service [IMPLEMENTED - Phase 1 & 2]
   ↓
[Future Safe SQL Builder & AST Validator - Phase 7]
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
- **Outputs:** Serialized API responses with correlation tracking, health/readiness telemetry.
- **Security Boundary:** Primary outer perimeter. Enforces CORS, correlation tracing, error redaction, and strict absence of arbitrary SQL or schema modification endpoints.
- **Dependencies:** FastAPI, Pydantic Settings, Uvicorn, Starlette.
- **Dependencies:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2.

### [3] Authentication Service
- **Status:** PLANNED (*Phase 5*)
- **Responsibility:** Authenticate institutional users and issue cryptographically signed JWT tokens.
- **Inputs:** User credentials (email/username, password, institutional SSO credentials).
- **Outputs:** Signed JWT containing user identity and assigned role claims.
- **Security Boundary:** Validates identity before allowing access to any downstream analytics service.
- **Dependencies:** PyJWT, Passlib (bcrypt).

### [4] RBAC & Scope Authorization Engine
- **Status:** PLANNED (*Phase 5*)
- **Responsibility:** Evaluate user roles (`MANAGEMENT`, `PRINCIPAL`, `DEAN`, `HOD`, `IQAC`) against requested metrics and data dimensions (e.g., restricting an HOD to their own department).
- **Inputs:** Authenticated user claims, requested metric ID, requested filters.
- **Outputs:** Mandatory scope constraints (e.g., `department_id = 'CSE'`) injected into the pipeline.
- **Security Boundary:** Critical security barrier. Enforced in Python backend code; cannot be overridden by user prompts or LLM output.
- **Dependencies:** Internal policy engine.

### [5] Agent 63 Orchestrator
- **Status:** PLANNED (*Phase 6*)
- **Responsibility:** Coordinates pipeline execution, manages conversational state, resolves follow-up questions, and handles error fallbacks.
- **Inputs:** User query string, conversation history, user scope context.
- **Outputs:** Orchestrated pipeline stages from intent to final presentation.
- **Security Boundary:** Isolates the LLM from database execution tools.
- **Dependencies:** FastAPI backend service layer.

### [6] Semantic Layer & Metric Catalog
- **Status:** PLANNED (*Phase 4*)
- **Responsibility:** Single source of truth for metric definitions, mathematical formulas, aggregation rules, dimensions, and null handling.
- **Inputs:** Metric identifiers requested by intent parser.
- **Outputs:** Formal metric specifications (source tables, required joins, formulas, filter constraints).
- **Security Boundary:** Eliminates metric hallucination; LLM cannot invent non-existent metrics.
- **Dependencies:** YAML/JSON catalog definitions.

### [7] Structured Intent Parser
- **Status:** PLANNED (*Phase 6*)
- **Responsibility:** Translates unstructured natural language into a strictly typed, validated intent schema.
- **Inputs:** Natural language question, available metric catalog summaries.
- **Outputs:** Validated `IntentSchema` (Metric, Population, Time Period, Dimensions, Filters).
- **Security Boundary:** Schema validation prevents prompt injection from leaking into SQL generation.
- **Dependencies:** LLM API, Pydantic v2.

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
- **Status:** PLANNED (*Phase 7*)
- **Responsibility:** Constructs parameterized, read-only SQL queries combining the scoped intent, metric definition, and schema registry.
- **Inputs:** Scoped intent, metric mapping, physical schema metadata.
- **Outputs:** Parameterized SQL statement with bound values.
- **Security Boundary:** Never concatenates raw user strings directly into SQL clauses.
- **Dependencies:** SQLAlchemy Core query builder.

### [11] SQL Validator
- **Status:** PLANNED (*Phase 7*)
- **Responsibility:** Performs Abstract Syntax Tree (AST) inspection of every generated SQL string before execution. Rejects any query containing mutation statements or non-whitelisted functions.
- **Inputs:** Parameterized SQL string.
- **Outputs:** Approval boolean or rejection exception.
- **Security Boundary:** Hard perimeter protecting against SQL injection, DDL, and DML.
- **Dependencies:** `sqlglot` or internal AST parser.

### [12] Read-Only Query Executor
- **Status:** PLANNED (*Phase 8*)
- **Responsibility:** Connects to the college-provided database using strictly read-only database credentials with query execution timeouts (e.g., 5-second max).
- **Inputs:** Validated SQL and parameters.
- **Outputs:** Raw tabular query result set.
- **Security Boundary:** Database-level read-only user privileges.
- **Dependencies:** SQLAlchemy, DBAPI drivers.

### [13] College-Provided Database(s)
- **Status:** Authoritative Institutional Source (*Inspected in Phase 1*)
- **Responsibility:** Stores official institutional operational and academic data.
- **Inputs:** Read-only `SELECT` queries.
- **Outputs:** Authoritative institutional records.
- **Security Boundary:** Physically and logically isolated. Write access is strictly prohibited.
- **Dependencies:** College IT infrastructure.

### [14] Result Validator
- **Status:** PLANNED (*Phase 8*)
- **Responsibility:** Validates result integrity: checks expected columns, validates data types, handles nulls, and verifies physical bounds (e.g., attendance percentage between 0 and 100).
- **Inputs:** Tabular database result set, metric boundary rules.
- **Outputs:** Validated numerical/tabular dataset or validation error.
- **Security Boundary:** Prevents presentation of corrupt, impossible, or hallucinated numbers.
- **Dependencies:** Pydantic validators.

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
