# Agent 63 – Development Phases Roadmap (Phases 0–16)

> **Execution Discipline:** Incremental development strictly one phase at a time.  
> **Rule:** No phase may begin until the preceding phase is verified, tested, and formally approved.

---

## Phase 0: Project Foundation + Architecture + UI Design System
- **Objective:** Establish the foundational repository structure, comprehensive architecture, security rules, environment templates, and institutional UI design system.
- **Major Tasks:**
  - Inspect repository and initialize folder layout with `.gitkeep` files.
  - Create hardened `.gitignore` and `.env.example`.
  - Author complete documentation (`README.md`, `architecture.md`, `requirements.md`, `security.md`, `development-phases.md`, `development-checklist.md`, `ui-design.md`).
  - Create institutional branding assets directory and documentation.
  - Execute repository verification checks.
- **Expected Deliverables:** Clean repository structure, full documentation suite, branding folder setup.
- **Acceptance Criteria:** All Phase 0 checklist items passed; zero code from Phase 1+ implemented.
- **Dependencies:** None.

---

## Phase 1: College Database Inspection + Safe Integration + Schema Mapping
- **Status:** COMPLETED
- **Objective:** Inspect the authoritative college-provided database (`schema_full.sql`), document its real schema, and build a controlled schema registry without mutating the database.
- **Completed Tasks:**
  - Confirmed target database engine: PostgreSQL 14+ with pgcrypto, pg_trgm extensions.
  - Cataloged all 21 schemas, 225 tables, 11 views, 11 functions, 7 RLS-enabled tables, and 19 security policies.
  - Generated full Schema Inventory (`database/schema/college_schema_inventory.json`).
  - Created Machine-Readable Schema Registry (`database/mappings/agent63_schema_registry.json`) across 5 access levels.
  - Built comprehensive Data Dictionary (`database/schema/college_data_dictionary.md`).
  - Mapped institutional entity relationships and analytical grains (`database/schema/college_relationships.md`).
  - Established Sensitivity Classification (`database/schema/sensitivity-classification.md`) strictly isolating `confidential` schema.
  - Documented Analytical Quirks & Data Quality Considerations (`database/schema/data-quality-considerations.md`).
  - Defined Initial Analytics Scope across 9 core domains (`database/mappings/initial_analytics_scope.md`).
  - Established Read-Only Integration architecture and timeout controls (`database/documentation/read-only-integration.md`).
  - Documented Database RLS & Security Integration (`database/documentation/database-security-integration.md`).
  - Implemented Schema Registry Validator (`scripts/validate_schema_registry.py`) and Unit Test Suite (`tests/test_schema_registry.py`).
- **Deliverables:** Complete set of 9 documentation & JSON files, validation script, and unit tests.
- **Acceptance Criteria:** Zero modifications/writes to college database; no synthetic university tables created; live connection unconfigured; all registry tests pass.
- **Dependencies:** Phase 0.

---

## Phase 2: FastAPI Backend Foundation [COMPLETED - Ready for Review]
- **Objective:** Establish a robust, production-grade FastAPI application structure with configuration management, health endpoints, modular routing, and safe service abstractions.
- **Completed Tasks:**
  - Set up Python virtual environment and core dependencies (`fastapi`, `uvicorn`, `pydantic-settings`, `httpx`, `pytest`).
  - Implemented modular backend directory structure (`app/api/v1/`, `app/core/`, `app/schemas/`, `app/services/`, `app/dependencies/`).
  - Created liveness (`/api/v1/health`) and readiness (`/api/v1/health/ready`) probes distinguishing app health from unconfigured database state.
  - Implemented request correlation middleware (`X-Request-ID`), structured JSON logging with credential scrubbing, centralized error handling, and CORS restrictions.
  - Implemented `SchemaRegistryService` consuming authoritative Phase 1 `agent63_schema_registry.json`.
  - Implemented safe `CollegeDatabaseService` abstraction (unconfigured default, no arbitrary SQL execution).
  - Built comprehensive backend test harness with 24 passing unit tests.
- **Deliverables:** `backend/app/`, `backend/tests/`, `backend/requirements.txt`, `backend/README.md`, `docs/backend.md`.
- **Acceptance Criteria Met:** Server starts cleanly without PostgreSQL; `/health` returns `200 OK`; all 24 backend tests pass; all 8 Phase 1 tests remain passing; zero arbitrary SQL endpoints exist.
- **Dependencies:** Phase 0, Phase 1.

---

## Phase 3: React Frontend + Institutional UI [COMPLETED - Ready for Review]
- **Objective:** Build the institutional frontend application using React, Vite, and TypeScript, implementing the institutional visual design system.
- **Completed Tasks:**
  - Initialized Vite + React 18 + TypeScript project with strict Vanilla CSS tokens and responsive layout.
  - Built Institutional Header with official logo area, project identity (`AGENT 63`), and accreditation badge cluster.
  - Implemented responsive navigation layout (Sidebar navigation, Header, Main content, and Bottom status bar).
  - Created initial routes: `/` (Overview), `/agent` (Conversational Workspace Foundation), `/analytics` (Analytics Workspace Foundation).
  - Built reusable UI components (`Card`, `Button`, `Input`, `StatusBadge`, `EmptyState`, `MetricPlaceholder`, `ChartPlaceholder`, `DataTablePlaceholder`).
  - Integrated live backend health check abstraction (`src/services/api.ts`) connecting to Phase 2 FastAPI `/api/v1/health` and `/health/ready`.
  - Enforced zero fabricated data, zero database queries, and zero artificial statistics.
- **Deliverables:** `frontend/src/`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/README.md`.
- **Acceptance Criteria Met:** Frontend builds cleanly (`npm run build` succeeds in 16s with 0 errors); visual styling matches the institutional design system; all existing 32 backend and Phase 1 tests pass.
- **Dependencies:** Phase 0, Phase 2.

---

## Phase 4: Semantic Layer + Metric Catalog [COMPLETED - Ready for Review]
- **Objective:** Define institutional business metrics, formulas, aggregations, and dimensions in a version-controlled semantic catalog.
- **Completed Tasks:**
  - Defined 26 core institutional metrics across 6 domains (Attendance, Assessment, Outcomes, Placement, Academics, Quality).
  - Defined 10 controlled analytical dimensions mapped to Phase 1 database objects and columns.
  - Built deterministic join path registry with 24 verified foreign-key relational paths (`semantic_layer/joins/join_paths.json`).
  - Formulated semantic security policy (`semantic_layer/policies/semantic_security.json`) enforcing confidential domain exclusion, exam security isolation, and placement fairness.
  - Implemented master registry compiler generating `semantic_layer/registry/semantic_registry.json`.
  - Built automated semantic layer validator (`scripts/validate_semantic_layer.py`) verifying 100% schema registry compliance.
  - Implemented backend `SemanticRegistryService` (`backend/app/services/semantic_registry.py`) providing in-memory read-only lookups.
  - Created automated test suites (`tests/test_semantic_layer.py` and `backend/tests/test_semantic_registry_service.py`) with 18 passing tests.
- **Deliverables:** `semantic_layer/`, `scripts/validate_semantic_layer.py`, `backend/app/services/semantic_registry.py`, test suites, and documentation.
- **Acceptance Criteria Met:** All metrics linked to real schema objects; zero confidential exposures; validator reports 0 errors and 0 warnings; all 50 tests pass.
- **Dependencies:** Phase 1, Phase 2.

---

## Phase 5: Authentication + RBAC [COMPLETED - Ready for Review]
- **Objective:** Implement a production-oriented Authentication + RBAC + Authorization foundation. (Actual production authentication requires the future college identity database integration).
- **Major Tasks Completed:**
  - Implemented Argon2id password verification (`backend/app/services/password.py`) using `argon2-cffi`.
  - Implemented JWT token generation and validation services (`backend/app/services/authentication.py`) using `PyJWT` with pinned HMAC-SHA256, minimal claims (`sub`, `jti`, `iat`, `nbf`, `exp`, `iss`, `aud`), and startup secret validation.
  - Built token revocation abstraction (`TokenRevocationStore`) using token `jti` identifiers with expiration pruning (ephemeral in-memory process-lifetime limitation documented; designed for future PostgreSQL/Redis persistence).
  - Implemented test fixture isolation: `InMemoryIdentityRepository` is strictly test-only; unconfigured production runtime fails closed via `UnavailableIdentityRepository`.
  - Implemented Scoped Authorization Engine (`backend/app/services/authorization.py`) mapping `principal -> role -> permission -> scope -> semantic sensitivity -> authorization decision`.
  - Established Server-Side Identity Authority: JWT role claims are never trusted blindly; roles and scopes are resolved server-side on each request.
  - Integrated Phase 4 Semantic Layer security policy: enforces `APPROVED` lifecycle gatekeeping, confidential schema blocking, and sensitivity tiers.
  - Built FastAPI auth dependencies (`extract_bearer_token`, `get_current_principal`, `require_roles`, `require_permissions`, `require_department_scope`).
  - Added Auth REST API endpoints: `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` with fail-closed behavior when disabled.
  - Implemented structured security audit logging with `X-Request-ID` and token/password scrubbing.
  - Authored comprehensive test suites (44 new unit and integration tests, 94 total passing).
- **Deliverables:** `backend/app/schemas/principal.py`, `backend/app/schemas/auth.py`, `backend/app/services/authentication.py`, `backend/app/services/authorization.py`, `backend/app/services/token_revocation.py`, `backend/app/services/identity_repository.py`, `backend/app/services/password.py`, `backend/app/services/audit.py`, `backend/app/dependencies/auth.py`, `backend/app/api/v1/auth.py`, and test suites.
- **Acceptance Criteria Met:** Unauthorized requests rejected with `401`/`403`; department/student scoping strictly prevents horizontal privilege escalation; token tampering and header manipulation are rejected; production cannot authenticate with test fixtures; zero live PostgreSQL or external LLM requirements; 94 passing tests.
- **Dependencies:** Phase 2, Phase 4.

---

## Phase 6: Natural Language → Structured Intent [COMPLETED - Ready for Review]
- **Objective:** Develop the Natural Language understanding pipeline that maps user questions into typed, validated structured intents using Google Gemini backend-only integration.
- **Major Tasks Completed:**
  - Installed and pinned `google-genai>=1.0.0` in `backend/requirements.txt` (zero OpenAI, zero LangChain).
  - Defined strict `StructuredIntent` Pydantic models (`backend/app/schemas/intent.py`) with fields for `intent_type`, `primary_metric_id`, `dimensions`, `filters`, `time_context`, `reasoning_summary`, and raw SQL injection filter guards.
  - Implemented Google Gemini client abstraction (`backend/app/services/gemini_client.py`) using official `google.genai.Client` and `types.GenerateContentConfig` with structured JSON schema enforcement, deterministic temperature 0.0, timeout guards, and deterministic `MockGeminiClient` for CI testing without API keys.
  - Implemented `IntentValidator` (`backend/app/services/intent_validator.py`) enforcing metric grounding in Phase 4 catalog, lifecycle status gatekeeping (`APPROVED` only; rejects `REVIEW_REQUIRED` and `DEPRECATED`), confidential domain isolation, dimension validity against Phase 4 dimensions, and SQL injection filter rejection.
  - Implemented `IntentService` (`backend/app/services/intent_service.py`) orchestrating dynamic system prompt compilation from approved Phase 4 catalog, few-shot institutional examples, Gemini invocation, validation, server-side `AuthorizationService.authorize_metric()` checking, and security audit logging.
  - Built protected API endpoint `POST /api/v1/intent` (`backend/app/api/v1/intent.py`) requiring `Depends(get_current_principal)` with uniform error mapping (`503` unconfigured, `504` timeout, `400` validation failure) and request correlation ID preservation.
  - Updated readiness probe (`/api/v1/health/ready`) to report Gemini configuration status.
  - Authored comprehensive test suite: 30 new unit and integration tests across 5 test files (`test_intent_schema.py`, `test_intent_validator.py`, `test_gemini_client.py`, `test_intent_service.py`, `test_intent_api.py`), bringing total passing test suite to 124 tests.
- **Deliverables:** `backend/app/schemas/intent.py`, `backend/app/services/gemini_client.py`, `backend/app/services/intent_validator.py`, `backend/app/services/intent_service.py`, `backend/app/api/v1/intent.py`, test suites, and documentation.
- **Acceptance Criteria Met:** 100% test pass rate (124/124 tests); zero SQL generation or database connection; exclusively Google Gemini SDK; prompt injection attempts quarantined; horizontal privilege escalation blocked server-side; schema registry and semantic layer validation scripts pass 100%; frontend builds cleanly with 0 errors.
- **Dependencies:** Phase 4, Phase 5.

---

## Phase 7: Structured Intent → Safe SQL [COMPLETED - Ready for Review]
- **Objective:** Transform validated intents and RBAC scopes into deterministic, parameterized, read-only SQL queries with AST-level safety verification.
- **Major Tasks Completed:**
  - Installed and pinned `sqlglot>=25.0.0` for PostgreSQL AST inspection.
  - Defined `SQLArtifact` and `SQLCompilationStatus` Pydantic schemas (`backend/app/schemas/sql_artifact.py`).
  - Added query limit settings (`DEFAULT_QUERY_LIMIT = 100`, `MAX_QUERY_LIMIT = 1000`) and dedicated error classes (`SQLCompilationError`, `SQLValidationError`, `SQLAuthorizationError`).
  - Implemented `SQLValidator` (`backend/app/services/sql_validator.py`) with AST-level inspection enforcing: single statement, `exp.Select` only, no `SELECT *`, no SQL comments, schema allowlist, table allowlist via Schema Registry, function allowlist, mandatory positive limit <= 1000, and rejection of all mutation tokens (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.).
  - Implemented `SQLCompiler` (`backend/app/services/sql_compiler.py`) compiling 5 query archetypes (`METRIC_QUERY`, `BREAKDOWN_QUERY`, `COMPARISON_QUERY`, `TREND_QUERY`, `RANKING_QUERY`) with strict parameter separation and server-side authorization scoping (STUDENT self-scope, HOD departmental scope).
  - Integrated `compile_intent_to_sql` method on `IntentService`.
  - Authored comprehensive test suites: 30 new tests across `test_sql_compiler.py`, `test_sql_validator.py`, and `test_sql_golden_snapshots.py`, bringing total passing test suite to 187 tests.
- **Deliverables:** `backend/app/schemas/sql_artifact.py`, `backend/app/services/sql_validator.py`, `backend/app/services/sql_compiler.py`, updated `intent_service.py`, comprehensive test suites, updated documentation.
- **Acceptance Criteria Met:** 100% test pass rate (187/187 tests); zero database connections or executions; strictly read-only parameterized queries; zero SQL comments or multiple statements; server-side authorization scoping enforced; schema registry and semantic layer validation scripts pass 100%; frontend builds cleanly.
- **Dependencies:** Phase 1, Phase 4, Phase 5, Phase 6.


---

## Phase 8: Safe Query Execution + Result Validation [COMPLETED - Ready for Review]
- **Objective:** Safely execute read-only queries against the college PostgreSQL database, enforce hard resource limits and statement timeouts, and validate numerical results against domain sanity bounds.
- **Major Tasks Completed:**
  - Installed and pinned `psycopg[binary]>=3.1.0` (version 3.3.5) for high-performance PostgreSQL interaction.
  - Defined Pydantic query result schemas (`backend/app/schemas/query_result.py`): `QueryResultStatus`, `ExecutionMetadata`, `QueryResult`, `AgentQueryRequest`, `AgentQueryResponse`.
  - Added Phase 8 configuration settings in `backend/app/core/config.py`: `COLLEGE_DB_MIN_POOL_SIZE = 1`, `COLLEGE_DB_MAX_POOL_SIZE = 10`, `MAX_RESULT_ROWS = 1000`, `MAX_RESULT_BYTES = 1048576`.
  - Implemented domain exceptions in `backend/app/core/errors.py`: `DatabaseNotConfiguredError` (503), `DatabaseConnectionError` (503), `DatabaseTimeoutError` (504), `DatabaseExecutionError` (500), `ResultValidationError` (422), `ResultSizeLimitExceededError` (413), and `SecurityValidationError` (400).
  - Upgraded `CollegeDatabaseService` (`backend/app/services/database.py`) with:
    - Fail-closed handling when database is unconfigured.
    - Parameter translation from `:param` to `%(param)s` preserving PostgreSQL type casts (`::text`, `::integer`, `::numeric`).
    - Enforced read-only transaction mode (`conn.read_only = True`, `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;`).
    - PostgreSQL statement timeout enforcement (`SET statement_timeout = <ms>;`).
    - Row count and byte payload size guardrails.
  - Implemented `ResultValidator` (`backend/app/services/result_validator.py`) with:
    - Empty result set handling (`QueryResultStatus.EMPTY`).
    - IEEE-754 safety: strictly rejects `NaN`, `Infinity`, and `-Infinity`.
    - Physical domain sanity bounds (percentages [0, 100], non-negative counts >= 0, rubric scales [0, 3]).
    - Strict NULL preservation as `None`.
    - Type normalization (Decimals to floats, dates/datetimes to ISO-8601).
  - Implemented `ExecutionService` (`backend/app/services/execution_service.py`) with pre-execution defense-in-depth checks, read-only database execution orchestration, and audit event dispatch (`QUERY_EXECUTED`, `QUERY_FAILED`).
  - Implemented and mounted protected API route `POST /api/v1/agent/query` (`backend/app/api/v1/agent.py`) supporting end-to-end execution and dry-run SQL inspection.
  - Updated frontend `ApiService` (`frontend/src/services/api.ts`) and `AgentPage` (`frontend/src/pages/AgentPage.tsx`) to display compiled SQL, execution metadata, and results in clean data tables without charts.
  - Authored comprehensive test suites: 29 new unit and integration tests across 4 test files (`test_database_service.py`, `test_result_validator.py`, `test_execution_service.py`, `test_agent_query_api.py`), bringing total passing tests to 229.
- **Deliverables:** `backend/app/schemas/query_result.py`, updated `database.py`, `backend/app/services/result_validator.py`, `backend/app/services/execution_service.py`, `backend/app/api/v1/agent.py`, updated router and frontend, test suites, updated documentation.
- **Acceptance Criteria Met:** 100% test pass rate (229/229 tests); read-only execution exclusively; zero mutations; statement timeouts enforced; domain sanity bounds checked; fail-closed when database is unconfigured (HTTP 503); zero synthetic data; schema registry and semantic layer validation pass 100%; frontend builds cleanly.
- **Dependencies:** Phase 1, Phase 7.

---

## Phase 9: Charts + Conversational Analytics UI
- **Objective:** Connect frontend and backend to render interactive result cards and Recharts visualizations.
- **Major Tasks:**
  - Build backend chart specification generator (maps results to Recharts schemas).
  - Implement frontend Institutional Result Card (Metric Value, Formula, Period, Filters, Verification Tag).
  - Implement Recharts components (Bar, Line, Distribution, KPI cards) using institutional color tokens.
  - Integrate conversational question input and history display.
- **Expected Deliverables:** End-to-end interactive conversational UI displaying charts and result cards.
- **Acceptance Criteria:** Questions display rich result cards and interactive charts matching institutional visual language.
- **Dependencies:** Phase 3, Phase 8.

---

## Phase 10: Follow-up Conversation Context
- **Objective:** Enable natural multi-turn conversations with contextual inheritance.
- **Major Tasks:**
  - Implement structured session state management in FastAPI.
  - Support context carryover (e.g., inheriting department/metric when user asks "What about 2024?").
  - Ensure conversational context never bypasses or relaxes RBAC boundaries.
  - Add explicit "Reset Conversation" capability.
- **Expected Deliverables:** Context resolution service, multi-turn conversation test suite.
- **Acceptance Criteria:** Follow-up questions resolve accurately without losing prior constraints; security scope re-validated on every turn.
- **Dependencies:** Phase 6, Phase 9.

---

## Phase 11: Anomaly Detection
- **Objective:** Implement statistical anomaly detection to alert administrators to unusual patterns.
- **Major Tasks:**
  - Build explainable statistical algorithms (moving averages, percentage changes, standard deviation thresholds).
  - Identify sudden drops in attendance, pass rate outliers, or enrollment spikes.
  - Render anomaly indicator badges on result cards with baseline, threshold, and deviation data.
- **Expected Deliverables:** Anomaly detection service, statistical unit tests, UI alert badges.
- **Acceptance Criteria:** Flags genuine statistical outliers; provides transparent mathematical evidence without hallucinating causes.
- **Dependencies:** Phase 8, Phase 9.

---

## Phase 12: Role-Based Dashboards + Scheduled Refresh
- **Objective:** Implement pre-configured executive dashboards tailored to each institutional role.
- **Major Tasks:**
  - Build dashboard view templates for Management, Principal, Dean, HOD, and IQAC.
  - Implement background refresh scheduler for caching intensive KPI queries.
  - Connect dashboard cards to the Semantic Layer.
- **Expected Deliverables:** Role-based dashboard views, scheduled refresh workers, cached metric endpoints.
- **Acceptance Criteria:** Each role accesses only their authorized dashboard; dashboards render cached metrics instantaneously.
- **Dependencies:** Phase 5, Phase 9, Phase 11.

---

## Phase 13: Query Logging + Popular Questions
- **Objective:** Maintain comprehensive audit logs and capture institutional questioning patterns.
- **Major Tasks:**
  - Implement structured audit logger recording query hash, user ID, role, duration, and status.
  - Scrub all passwords, tokens, and PII from log streams.
  - Build "Frequently Asked Institutional Questions" suggestion service.
- **Expected Deliverables:** Audit logging middleware, telemetry database/store, suggested questions component.
- **Acceptance Criteria:** Immutable audit log maintained; sensitive secrets completely sanitized.
- **Dependencies:** Phase 5, Phase 8.

---

## Phase 14: Export + Official Report Verification
- **Objective:** Provide authorized data exports and distinguish between ad-hoc analytics and official statutory figures.
- **Major Tasks:**
  - Implement CSV and Excel export generators with full metadata headers.
  - Enforce RBAC export permissions.
  - Implement Official Report Verification tag referencing reconciliation checkpoints (e.g., NAAC/AISHE figures).
- **Expected Deliverables:** Export API endpoints, export UI triggers, official verification status badges.
- **Acceptance Criteria:** Exports include audit headers and respect row-level scoping; official figures clearly demarcated.
- **Dependencies:** Phase 8, Phase 9, Phase 12.

---

## Phase 15: Security + Accuracy + Adversarial Testing
- **Objective:** Subject the complete platform to comprehensive adversarial, security, and mathematical verification tests.
- **Major Tasks:**
  - Execute automated prompt injection test suite.
  - Run SQL injection penetration tests against the API and AST validator.
  - Verify horizontal privilege separation across all roles.
  - Reconcile Agent 63 outputs against known manual institutional calculations.
- **Expected Deliverables:** Security audit report, adversarial penetration test suite, accuracy verification matrix.
- **Acceptance Criteria:** 100% pass rate on security tests; zero injection vulnerabilities; exact mathematical reconciliation.
- **Dependencies:** Phases 1–14.

---

## Phase 16: Deployment + Final Demonstration
- **Objective:** Package the application for institutional deployment and conduct final demonstration.
- **Major Tasks:**
  - Prepare production build artifacts and environment validation scripts.
  - Author deployment guide and administrator operations manual.
  - Conduct full institutional demonstration and viva readiness rehearsal.
- **Expected Deliverables:** Production-ready application package, deployment documentation, viva demonstration script.
- **Acceptance Criteria:** Clean deployment in college staging environment; all demonstration workflows execute smoothly.
- **Dependencies:** Phases 0–15.
