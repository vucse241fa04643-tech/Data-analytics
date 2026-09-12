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

## Phase 9: Charts + Conversational Analytics UI [COMPLETED - Ready for Review]
- **Objective:** Transform the validated raw query execution experience into an accessible, institutional conversational analytics presentation layer with deterministic chart selection, KPI cards, responsive Bar/Line charts, deterministic analytical summaries, and metadata audit drilldowns.
- **Key Architectural Rules & Constraints:**
  - **Presentation Layer Exclusivity:** The frontend remains strictly a presentation layer. Backend remains authoritative for auth, RBAC, semantic catalog, SQL compilation, AST verification, and read-only PostgreSQL execution.
  - **Deterministic Visualization Selection:** Chart types are chosen strictly by deterministic rules (Rules A–E) derived from validated `QueryResult` column data types, row counts, and Semantic Layer metadata. Zero LLM/Groq calls are made for visualization decisions.
    - *Rule A (KPI):* 1 numeric metric with 1 result row -> KPI card.
    - *Rule B (Bar / Horizontal Bar):* 1 categorical dimension + 1 numeric metric -> Column or Horizontal Bar chart.
    - *Rule C (Line):* 1 temporal dimension (academic year, term, date) + 1 numeric metric -> Line chart.
    - *Rule D (Table):* Multiple dimensions or complex multi-grouping results -> Table view.
    - *Rule E (None / Table):* Empty or unsupported result shapes -> Table or None.
  - **Deterministic Analytical Explanation:** Pure factual summaries synthesized without LLMs, referencing metric definitions, units, boundaries (highest/lowest), and returned dimensions. Strictly prohibits fabricated causal claims (no unsupported "because..." statements).
  - **Universal Accessible Representation:** Every chart is accompanied by a fully accessible, semantic data table (`ResultTableView`) with right-aligned numbers and explicit `NULL` rendering.
  - **Scope Boundaries Preserved:** No conversational memory (deferred to Phase 10), no anomaly detection (deferred to Phase 11), and no exports (deferred to Phase 14).
- **Major Implementations:**
  - `backend/app/schemas/visualization.py`: Pydantic `VisualizationDescriptor` and `ChartType` enum.
  - `backend/app/services/visualization_service.py`: `VisualizationService` implementing Rules A–E and deterministic explanation synthesis.
  - `backend/app/schemas/query_result.py`: Extended `AgentQueryResponse` with `visualization`, `explanation`, and `metric_display_name`.
  - `backend/app/api/v1/agent.py`: Integrated `VisualizationService` into analytical query pipeline.
  - `frontend/package.json`: Installed `recharts` (`^3.10.1`) for responsive, accessible charting.
  - `frontend/src/types/index.ts`: Added frontend TypeScript interfaces matching backend visualization models.
  - `frontend/src/components/analytics/`: Created `KpiCard`, `BarChartCard`, `LineChartCard`, `AnalyticalSummaryCard`, `ResultTableView`, and `QueryDetailsAccordion`.
  - `frontend/src/pages/AgentPage.tsx`: Reorganized results canvas into the authoritative Phase 9 hierarchy:
    1. Query Title Banner & Trace Header
    2. Result Summary (KPI Card for single metrics)
    3. Appropriate Visual Representation (KPI, Bar Chart, or Line Chart)
    4. Analytical Summary (Deterministic narrative)
    5. Result Table (Universal accessible companion)
    6. Query Details & Institutional Governance Audit Accordion
  - `backend/tests/test_visualization_service.py`: 10 comprehensive tests verifying Rules A–E, null handling, empty results, and zero-LLM calls.
- **Expected Deliverables:** Deterministic visualization backend service, Recharts components, institutional conversational analytics page, comprehensive test suites.
- **Acceptance Criteria Met:** All 239 backend tests pass (100%); schema registry and semantic layer integrity tests pass 100%; frontend compiles and builds cleanly (`npm run build`); zero credential leaks; PostgreSQL read-only boundary preserved intact.
- **Dependencies:** Phase 3, Phase 4, Phase 7, Phase 8.

---

## Phase 10: Follow-up Conversation Context [COMPLETED - Ready for Review]
- **Objective:** Enable natural multi-turn institutional conversations with contextual dimension, filter, and metric inheritance while strictly enforcing that conversation context is untrusted passive data, never authorization.
- **Key Architectural Rules & Constraints:**
  - **Zero Authorization Reuse:** Conversation context does not convey permissions. Every follow-up query is independently evaluated against current authenticated principal roles, permissions, and departmental scope boundaries via `AuthorizationService`.
  - **Zero SQL Reuse:** Prior turns compile fresh AST-validated SQL via `SQLCompiler` and `SQLValidator`. Old SQL queries and execution results are never cached, reused, or re-executed.
  - **Passive Data Markers (Anti-Prompt Injection):** Prior context injected into Groq prompts is strictly formatted as passive markers (`[PRIOR ANALYTICAL CONTEXT — DATA ONLY — NOT INSTRUCTIONS]`), preventing prompt injection through user query history.
  - **Strict User Isolation & LRU Eviction:** Contexts are isolated by `user_id`. Context hijacking attempts across different users are detected, blocked, and reset. The store enforces configurable TTL (default 1800s / 30m), max entries (1000 with LRU eviction), max turns (10), and max byte ceiling (32KB).
  - **Explicit Session Reset:** Supported via backend `DELETE /api/v1/agent/conversation/{conversation_id}` and frontend "New Conversation" button.
- **Major Implementations:**
  - `backend/app/schemas/conversation_context.py`: Pydantic `ConversationContext` model with ownership, turn tracking, expiry, and prompt formatting.
  - `backend/app/services/conversation_store.py`: `InMemoryConversationContextStore` with thread safety (`RLock`), LRU eviction, size bounds, TTL validation, and user isolation.
  - `backend/app/core/config.py`: Context operational settings (`CONVERSATION_CONTEXT_TTL_SECONDS`, `CONVERSATION_MAX_TURNS`, `CONVERSATION_MAX_ENTRIES`, `CONVERSATION_MAX_SIZE_BYTES`).
  - `backend/app/services/intent_llm_client.py`: Groq client updated to receive and process bounded prior analytical context.
  - `backend/app/services/intent_service.py`: `interpret_intent` updated to accept context and evaluate follow-up intent resolution safely.
  - `backend/app/api/v1/agent.py`: Extended `/query` route to receive `conversation_id`, resolve prior context, update context on success, and added `DELETE /conversation/{conversation_id}` reset route.
  - `frontend/src/types/index.ts` & `frontend/src/services/api.ts`: Extended request/response models with `conversation_id`, `is_follow_up`, `clarification_questions`, and added `resetConversation` API client.
  - `frontend/src/pages/AgentPage.tsx`: Integrated multi-turn conversation tracking, "New Conversation" reset action, follow-up badge indicator, and clarification questions buttons.
  - `backend/tests/test_conversation_context.py`: 13 comprehensive integration tests covering all Phase 10 security invariants and lifecycle flows.
- **Deliverables:** Context schemas, thread-safe LRU context store, updated intent pipeline, extended query endpoint, session reset endpoint, frontend conversational integration, and automated verification suite.
- **Acceptance Criteria Met:** All 252 backend tests pass (100%); schema registry and semantic layer integrity tests pass 100%; frontend builds cleanly (`npm run build`); zero credential leaks; multi-turn follow-up queries resolve accurately without authorization relaxation.
- **Dependencies:** Phase 6, Phase 9.

---

## Phase 11: Deterministic Anomaly Detection [COMPLETED - Ready for Review]
- **Objective:** Implement a secure, 100% deterministic anomaly-detection layer that analyzes ONLY already-authorized and already-validated analytical results (`QueryResult`).
- **Core Security Invariant:**
  - Anomaly detection is an **ANALYTICS TRANSFORMATION, NOT A DATA ACCESS LAYER**.
  - Operates strictly AFTER authentication, RBAC, authorization, SQL compilation, AST validation, read-only PostgreSQL execution, and result validation.
  - Zero database queries, zero SQL generation/manipulation, zero LLM calls (neither Groq, Gemini, nor OpenAI), zero credential usage, zero scope expansion.
  - 100% deterministic: identical validated results and configuration produce identical anomaly assessments and factual explanations.
  - Factual explanations disclaim unsupported causal claims: *"The result does not establish the cause."*
  - **Baseline Governance Policy:** Configured anomaly thresholds are analytical detection parameters unless an authoritative institutional target is present. Configured thresholds (75.0% attendance, 60.0% pass rate, 2.0 attainment, 5% target deviation) are NEVER described as institutional policy, college policy, official threshold, or official benchmark.
  - Explicit baseline provenance is enforced via `BaselineType`: `OFFICIAL_TARGET` (authoritative target present in validated QueryResult row), `HISTORICAL_BASELINE` (derived from authorized multi-period observations), `ANALYTICAL_HEURISTIC` (configured analytical detection parameters), and `NO_BASELINE`.
- **Completed Tasks:**
  - `backend/app/schemas/anomaly.py`: Defined authoritative three-state assessment lifecycle (`NO_ANOMALY`, `ANOMALY_DETECTED`, `ASSESSMENT_UNAVAILABLE`), severity classifications (`NONE`, `LOW`, `MEDIUM`, `HIGH`), baseline provenance (`BaselineType`), methods (`TARGET_DEVIATION`, `CONFIGURED_THRESHOLD`, `PERCENTAGE_DEVIATION`, `HISTORICAL_Z_SCORE`, `CROSS_CATEGORY_IQR`, `INSUFFICIENT_DATA`), `CategoryAnomalyItem`, and `AnomalyAssessment`.
  - `backend/app/core/config.py`: Added configurable analytical benchmarks (`ANOMALY_DETECTION_ENABLED`, `ANOMALY_ATTENDANCE_THRESHOLD`, `ANOMALY_PASS_RATE_THRESHOLD`, `ANOMALY_ATTAINMENT_THRESHOLD`, `ANOMALY_HISTORICAL_MIN_OBSERVATIONS`, `ANOMALY_Z_SCORE_THRESHOLD`).
  - `backend/app/services/anomaly_service.py`: Implemented `AnomalyDetectionService` providing in-memory evaluation for single-KPI, categorical cross-sectional IQR distributions, and time-series historical z-score deviations with strict baseline provenance and non-policy governance wording.
  - `backend/app/schemas/query_result.py`: Added `anomaly: Optional[AnomalyAssessment]` to `AgentQueryResponse`.
  - `backend/app/api/v1/agent.py`: Integrated `AnomalyDetectionService` into the query pipeline immediately following result validation and visualization recommendation.
  - `frontend/src/types/index.ts`: Added TypeScript anomaly types including `BaselineType` and updated `AgentQueryResponse`.
  - `frontend/src/components/analytics/AnomalyInsightCard.tsx`: Built institutional accessible insight card displaying severity badge, baseline provenance badge, observed vs benchmark/target metrics, detection method, factual explanation with governance drawer, and non-alarmist UI.
  - `frontend/src/pages/AgentPage.tsx`: Integrated `AnomalyInsightCard` in the visual presentation hierarchy.
  - `backend/tests/test_anomaly_service.py` & `backend/tests/test_anomaly_api.py`: 31 comprehensive tests verifying all 30 prompt specifications, mathematical accuracy, security boundaries, Phase 10 compatibility, and governance regression tests (13a–13e).
- **Deliverables:** Anomaly schemas, deterministic detection service, API integration, institutional insight card, and 31 automated tests.
- **Acceptance Criteria Met:** All 283 backend tests pass (100%); schema registry and semantic layer integrity tests pass 100%; frontend builds cleanly (`npm run build`); zero credential leaks; no external LLM or DB calls in anomaly service.
- **Dependencies:** Phase 8, Phase 9, Phase 10.

---

## Phase 12: Role-Based Dashboards + Scheduled Refresh [COMPLETED - Ready for Review]
- **Objective:** Implement pre-configured executive and operational institutional dashboards tailored strictly to authenticated roles, backed by bounded in-memory caching and secure, re-authenticating scheduled refresh.
- **Mandatory Governance Principles:**
  - *Dashboard visibility is presentation only; backend authorization remains authoritative.*
  - *Scheduled refresh does not bypass authorization. Each refresh executes through the existing authorized analytical pipeline.*
  - *Zero raw SQL in dashboards, zero frontend metric/scope selection, zero LLM calls for dashboards.*
- **Major Tasks Completed:**
  - `backend/app/schemas/dashboard.py`: Defined comprehensive Pydantic models for widgets, dashboard definitions, catalog, execution responses, and schedule management.
  - `backend/app/services/dashboard_registry.py`: Built institutional dashboard registry mapping approved semantic metrics to 9 roles (Principal, Dean, HOD, Faculty, IQAC Director, Placement Officer, Controller of Examinations, Mentor, Student) while denying quarantined roles (Counsellor).
  - `backend/app/services/dashboard_service.py`: Implemented authoritative dashboard resolution, scoped role validation, bounded execution via thread pool, in-memory TTL caching with scope keying, and partial error isolation.
  - `backend/app/services/dashboard_scheduler.py`: Implemented in-process background refresh scheduler enforcing >= 60-minute interval, per-user capacity limits (5), system ceiling (50), and strict re-authorization of credentials on each refresh run.
  - `backend/app/api/v1/dashboard.py`: Built REST API endpoints (`/catalog`, `/{dashboard_id}`, `/{dashboard_id}/refresh`, `/schedules`).
  - `frontend/src/pages/RoleDashboardPage.tsx`: Developed institutional React/TypeScript dashboard UI with KPI grid, charts, anomaly insight cards, scheduled refresh drawer, and graceful widget-level error states.
  - `frontend/src/app/router.tsx` & `Sidebar.tsx`: Integrated role dashboard route `/dashboards` into institutional navigation.
  - `backend/tests/`: Created 28 new tests across service, scheduler, and API integration (`test_dashboard_service.py`, `test_dashboard_scheduler.py`, `test_dashboard_api.py`).
- **Deliverables:** Server-controlled dashboard registry, dashboard execution service, in-process scheduler, REST endpoints, institutional frontend dashboard page, and 28 automated tests.
- **Acceptance Criteria Met:** 311/311 backend tests passing (100%); schema registry and semantic layer integrity tests passing (100%); frontend builds cleanly (`npm run build`); zero raw SQL; zero LLM calls; Counsellor quarantined (403); full error isolation; scope boundaries strictly enforced.
- **Dependencies:** Phase 4, Phase 5, Phase 7, Phase 8, Phase 9, Phase 11.

---

## Phase 13: Query Logging + Popular Questions [COMPLETED - Ready for Review]
- **Objective:** Maintain bounded, thread-safe, privacy-safe analytical query logging and capture institutional questioning patterns without leaking secrets, credentials, raw SQL, raw rows, or user identities.
- **Mandatory Privacy & Architecture Invariants:**
  - *Storage is application-memory only*: The query logging store uses bounded in-memory LRU storage (`QUERY_LOG_MAX_ENTRIES=10000`) and a strict time window (`QUERY_LOG_AGGREGATION_WINDOW_HOURS=168`).
  - *Database persistence is intentionally absent*: Server restart clears query-log and popularity state.
  - *AgentOps database persistence is intentionally deferred*: Integration with college PostgreSQL `agentops.agent_run` is deferred because `agentops.agent_run` enforces a foreign key to `agentops.agent` (where Agent 63 does not have a provisioned row), and the institutional connection is strictly read-only. This design avoids creating a second persistent audit store or modifying the institutional schema.
  - *No synthetic popularity counts*: Popular questions are derived solely from real, observed analytical query events. Zero synthetic numbers or mock questions exist.
  - *Query logging is purely observational and NEVER an authorization source*: Authorization is always evaluated independently before executing any query and before surfacing any popular question candidate.
  - *Authorization evaluated per candidate*: Popular questions are filtered strictly to metrics and organizational scopes the authenticated principal is authorized to execute.
  - *Zero sensitive data leakage*: Zero SQL statements, zero credentials/JWTs/passwords, zero raw result rows, and zero user identifiers are persisted in events or exposed in outputs.
  - *Fail-open resilience*: Logging failure never aborts or corrupts analytical query execution.
- **Major Tasks Completed:**
  - `backend/app/schemas/query_log.py`: Defined `QueryLogEvent`, `QueryLogEventType`, `QueryLogStatus`, and `PopularQuestion` schemas.
  - `backend/app/services/query_log_service.py`: Implemented thread-safe in-memory `QueryLoggingService` with LRU eviction, role-based metric and scope authorization filtering, and aggregation engine.
  - `backend/app/api/v1/agent.py`: Integrated query logging into manual queries, dry runs, intent rejections, and conversational follow-ups.
  - `backend/app/services/dashboard_service.py` & `dashboard_scheduler.py`: Integrated widget refresh and scheduled refresh logging.
  - `backend/app/api/v1/analytics.py`: Implemented authenticated `GET /api/v1/analytics/popular-questions` endpoint.
  - `frontend/src/types/index.ts` & `frontend/src/services/api.ts`: Added `PopularQuestion` type and `getPopularQuestions()` API method.
  - `frontend/src/components/analytics/PopularQuestionsPanel.tsx`: Created privacy-first popular questions panel with aggregated frequency tags.
  - `frontend/src/pages/AgentPage.tsx`: Integrated `PopularQuestionsPanel` into the conversational analytics interface.
  - `backend/tests/test_query_log_service.py` & `backend/tests/test_analytics_api.py`: 40 comprehensive security, scope, and API integration tests.
- **Deliverables:** In-memory query logging service, popular questions recommender, analytics API, frontend panel, and 40 automated tests.
- **Acceptance Criteria Met:** 371/371 backend tests passing (100%); schema registry and semantic layer validation clean (0 errors, 0 warnings); frontend builds cleanly (`npm run build`); zero raw SQL, secrets, or user identities in log outputs; strict RBAC adherence.
- **Dependencies:** Phase 5, Phase 8, Phase 10, Phase 12.

---

## Phase 14: Export + Official Report Verification [COMPLETED - Ready for Review]
- **Objective:** Provide authorized data exports and deterministically distinguish between ad-hoc analytical query outputs and registered official institutional benchmark figures without LLM dependencies.
- **Completed Tasks:**
  - `backend/app/schemas/export.py`: Defined `ExportFormat` (CSV, JSON), `ExportRequest`, `ExportMetadata`, `ExportResponseJSON`, `VerificationStatus` (MATCH, MISMATCH, NOT_COMPARABLE, NOT_VERIFIED), `VerificationRequest`, `VerificationResult`, and server-side `ExportArtifact`.
  - `backend/app/services/export_artifact_store.py`: Built bounded, in-memory LRU store with thread-safe locks and TTL expiration (15 minutes / 1000 items) for caching analytical results by correlation `request_id`.
  - `backend/app/services/export_service.py`: Built export serialization service with mandatory re-authorization (student self-scope, HOD departmental boundary), cross-user ownership isolation, CSV formula injection defense (`=`, `+`, `-`, `@`, `\t`, `\r` neutralized with `'`) while preserving legitimate negative and positive numeric semantics (`-42`, `-3.14`, `85.5`, string `"-42"` converted to number), RFC 4180 escaping (commas, quotes, newlines, UTF-8 Unicode), distinct NULL preservation, row limit ceiling (`EXPORT_MAX_ROWS=1000`), byte ceiling (`EXPORT_MAX_BYTES=2MB`), and fail-open `EXPORT` query logging.
  - `backend/app/services/verification_service.py`: Implemented deterministic official report reconciliation engine with zero LLM calls, querying authoritative PostgreSQL schema objects (`quality.kpi_value` with `validated_at IS NOT NULL`, `quality.kpi_definition`, `knowledge.document`), returning `NOT_VERIFIED` when no validated official benchmark exists (zero synthetic benchmarks in production). Implements exact Decimal/equality comparison first, followed by mathematical IEEE-754 floating-point representation normalization (`FLOAT_REPRESENTATION_ABS_TOL = 1e-9`, strictly technical representation normalization, NOT an institutional tolerance), checking reporting periods and organizational scopes, and generating neutral institutional concordance statements (never claiming certification or accreditation).
  - `backend/app/api/v1/analytics.py`: Exposed authenticated `POST /api/v1/analytics/export` and `POST /api/v1/analytics/verify` endpoints with strict principal ownership validation.
  - `frontend/src/types/index.ts` & `frontend/src/services/api.ts`: Added export and verification types and client API methods (`exportResult`, `verifyResult`).
  - `frontend/src/components/analytics/ExportControls.tsx`: Accessible CSV and JSON download triggers with progress state and error/success alerts.
  - `frontend/src/components/analytics/VerificationCard.tsx`: Deterministic report comparison card displaying MATCH, MISMATCH, NOT_COMPARABLE, or NOT_VERIFIED with neutral governance notices (mathematical concordance, never false certification).
  - `frontend/src/pages/AgentPage.tsx`: Integrated `ExportControls` and `VerificationCard` into the query result layout.
  - `backend/tests/test_export_service.py`: 56 comprehensive automated unit, service, API, and security regression tests.
- **Deliverables:** Export and verification schemas, artifact cache store, serialization service, verification service, REST endpoints, UI controls, and 56 automated tests.
- **Acceptance Criteria Met:** 427/427 backend tests passing (100%); 56/56 Phase 14 tests passing; schema and semantic layer validations 100% clean (0 errors, 0 warnings); frontend builds cleanly with zero TypeScript errors (`npm run build`); zero raw SQL, secrets, or unescaped formulas; zero LLM calls in verification or export; strict RBAC and re-authorization enforced; strictly zero database mutations or synthetic institutional benchmarks.
- **Dependencies:** Phase 8, Phase 9, Phase 12, Phase 13.

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
