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

## Phase 6: Natural Language → Structured Intent
- **Objective:** Develop the Natural Language understanding pipeline that maps user questions into typed, validated structured intents.
- **Major Tasks:**
  - Define `IntentSchema` Pydantic models (Metric, Population, Academic Period, Dimensions, Filters).
  - Construct prompt engineering templates referencing the Metric Catalog.
  - Integrate LLM API call with JSON mode/structured output enforcement.
  - Build intent validation logic with clarification fallbacks for ambiguous inputs.
- **Expected Deliverables:** Intent parser service, structured prompt templates, intent validation test suite.
- **Acceptance Criteria:** Unstructured questions reliably translate to valid `IntentSchema`; out-of-scope questions handled gracefully.
- **Dependencies:** Phase 4, Phase 5.

---

## Phase 7: Structured Intent → Safe SQL
- **Objective:** Transform validated intents and RBAC scopes into deterministic, parameterized, read-only SQL queries.
- **Major Tasks:**
  - Implement query builder mapping `IntentSchema` and metric definitions to SQL statements.
  - Inject mandatory RBAC filters (e.g., `WHERE department_id = :dept_id`).
  - Build AST-based SQL Validator (`sqlglot` or custom parser) to verify read-only semantics.
  - Enforce rejection of all mutation tokens (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.).
- **Expected Deliverables:** Safe SQL generator, AST SQL validator, SQL unit tests.
- **Acceptance Criteria:** Generated queries use parameter binding; any query with mutation keywords is rejected immediately.
- **Dependencies:** Phase 1, Phase 4, Phase 6.

---

## Phase 8: Safe Query Execution + Result Validation
- **Objective:** Safely execute read-only queries against the college database and validate numerical results.
- **Major Tasks:**
  - Configure isolated, read-only database connection pool with execution timeouts.
  - Execute parameterized SQL queries against the college database.
  - Implement result validation engine: check data types, null counts, and logical boundaries (e.g., $0\% \le \text{attendance} \le 100\%$).
  - Format tabular and aggregate results for presentation.
- **Expected Deliverables:** Read-only execution service, result validation module, query timeout guards.
- **Acceptance Criteria:** Queries execute within timeout limits; result validation flags impossible numbers; zero write capabilities.
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
