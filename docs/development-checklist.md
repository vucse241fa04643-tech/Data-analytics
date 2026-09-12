# Agent 63 – Master Development Checklist

> **Tracking Standard:** Every item in a phase must be marked complete (`[x]`) before proceeding to the subsequent phase.

---

## Phase 0: Project Foundation + Architecture + UI Design System
- [x] Repository inspected and current state understood
- [x] Existing work understood and preserved
- [x] Clean project structure established with `.gitkeep` files
- [x] `README.md` created with complete architecture, rules, and phase roadmap
- [x] `docs/architecture.md` created with component flow and security boundaries
- [x] `docs/requirements.md` created with complete functional & non-functional requirements
- [x] `docs/security.md` created with non-negotiable security rules and threat model
- [x] `docs/development-phases.md` created detailing Phases 0 through 16
- [x] `docs/development-checklist.md` created tracking all phases
- [x] `docs/ui-design.md` created documenting institutional design tokens and layout
- [x] `.gitignore` created and verified to protect secrets and temporary files
- [x] `.env.example` created with placeholder values only
- [x] Institutional branding asset directory (`frontend/public/assets/branding/`) created
- [x] Strict rule: No real credentials or secrets committed
- [x] Strict rule: No database created
- [x] Strict rule: No database connection created
- [x] Strict rule: No synthetic institutional data created
- [x] Strict rule: No AI agent created
- [x] Strict rule: No SQL generation created
- [x] Strict rule: No authentication created
- [x] Strict rule: No RBAC created
- [x] Strict rule: No analytics functionality created
- [x] Strict rule: No dashboards created
- [x] Strict rule: No unnecessary dependencies added
- [x] Basic repository and git safety checks passed

---

## Phase 1: College Database Inspection + Safe Integration + Schema Mapping
- [x] Repository inspected and Phase 0 work preserved
- [x] College schema (`schema_full.sql` / `01_foundation.sql`) identified as authoritative source of truth
- [x] PostgreSQL 14+ confirmed from supplied schema
- [x] All 21 schemas inventoried (`database/schema/college_schema_inventory.json`)
- [x] All 225 tables inventoried with columns, primary keys, and foreign keys
- [x] All 11 views cataloged and analyzed
- [x] Important constraints and entity relationships documented (`database/schema/college_relationships.md`)
- [x] Analytical grains and central academic grain (`academics.course_offering`) documented
- [x] Important analytical views documented (`attendance.v_current_attendance`, `assessment.v_course_performance`, etc.)
- [x] Sensitivity classification created (`database/schema/sensitivity-classification.md`)
- [x] Confidential schema isolated with non-negotiable `DENY_GENERAL_ANALYTICS`
- [x] Restricted objects identified (`assessment.question_paper`, credentials, exams)
- [x] Initial Agent 63 analytics scope defined across 9 core domains (`database/mappings/initial_analytics_scope.md`)
- [x] Machine-readable Agent 63 schema registry created (`database/mappings/agent63_schema_registry.json`)
- [x] Registry validated via automated tool (`scripts/validate_schema_registry.py`)
- [x] Read-only integration documented with least privilege and timeout controls (`database/documentation/read-only-integration.md`)
- [x] Strict rule confirmed: No synthetic college database created
- [x] Strict rule confirmed: No fake institutional data created
- [x] Strict rule confirmed: Zero college database modifications made
- [x] Strict rule confirmed: No credentials committed or exposed
- [x] Security and isolation tests pass (`tests/test_schema_registry.py`)
- [x] Documentation updated across all docs
- [x] No Phase 2 implementation started

---

## Phase 2: FastAPI Backend Foundation [COMPLETED - Ready for Review]
- [x] Initialized Python environment (.venv) with core FastAPI dependencies
- [x] Implemented modular directory structure (`backend/app/api/v1/`, `core/`, `schemas/`, `services/`, `dependencies/`)
- [x] Created centralized configuration management using Pydantic Settings
- [x] Implemented `/api/v1/health` (liveness) and `/api/v1/health/ready` (readiness) endpoints
- [x] Configured institutional CORS policies and centralized exception handlers
- [x] Implemented request correlation IDs (`X-Request-ID`) and structured JSON logging with secret scrubbing
- [x] Implemented `SchemaRegistryService` consuming Phase 1 registry (`agent63_schema_registry.json`)
- [x] Implemented safe `CollegeDatabaseService` abstraction (unconfigured default, no arbitrary SQL)
- [x] Audited route surface to ensure zero arbitrary SQL or bypass endpoints exist
- [x] Set up `pytest` test harness and verified 24 passing backend tests without PostgreSQL
- [x] Verified Phase 1 tests (8/8) and schema registry validation script remain passing
- [x] Documented backend in `docs/backend.md` and `backend/README.md`
- [x] Verified Phase 3 not started

---

## Phase 3: React Frontend + Institutional UI [COMPLETED - Ready for Review]
- [x] Initialized Vite + React 18 + TypeScript project structure
- [x] Implemented centralized CSS design tokens matching institutional reference (`tokens.css`)
- [x] Built Institutional Header with College Wordmark area, Project Identity (`AGENT 63`), and Accreditation badges
- [x] Implemented responsive application layout (`AppShell`, `Sidebar`, `StatusBar`)
- [x] Implemented bottom institutional status bar displaying live backend and registry telemetry
- [x] Rendered official logo placeholders with clear asset guidelines in `frontend/public/assets/branding/`
- [x] Created routes: `/` (Overview), `/agent` (Conversational Workspace), `/analytics` (Analytics Workspace)
- [x] Verified zero fabricated data, zero mock numbers, and zero SQL queries
- [x] Verified clean, error-free frontend build (`tsc -b && vite build` passed)
- [x] Verified Phase 4 not started

---

## Phase 4: Semantic Layer + Metric Catalog [COMPLETED - Ready for Review]
- [x] Cataloged 26 institutional metrics across 6 operational domains based on Phase 1 schema
- [x] Defined unambiguous mathematical formulas, grains, aggregations, time semantics, and null rules
- [x] Defined 10 controlled analytical dimensions mapped to Phase 1 database objects
- [x] Established deterministic join path registry with 24 verified foreign-key relational paths
- [x] Defined semantic security policy isolating `confidential.*` and enforcing placement fairness
- [x] Compiled machine-readable master registry (`semantic_layer/registry/semantic_registry.json`)
- [x] Implemented automated semantic layer validator (`scripts/validate_semantic_layer.py`)
- [x] Implemented in-memory backend service (`backend/app/services/semantic_registry.py`)
- [x] Wrote 18 unit and security tests covering semantic integrity and service lookups (50 total passing)
- [x] Documented semantic architecture and governance in `semantic_layer/README.md`
- [x] Confirmed zero live PostgreSQL installation, zero arbitrary SQL, zero LLM integration, and zero synthetic data

---

## Phase 5: Authentication + RBAC [COMPLETED - Ready for Review]
- [x] Implement JWT authentication service and password hashing (`Argon2id` via `argon2-cffi`, `PyJWT`)
- [x] Implement user models and role claims based on college `identity.*` schema (`STUDENT`, `FACULTY`, `MENTOR`, `HOD`, `DEAN`, `COE`, `IQAC`, `PLACEMENT`, `ACCOUNTS`, `COUNSELLOR`, `PRINCIPAL`, `ADMIN`)
- [x] Build backend token revocation abstraction (`TokenRevocationStore` with JTI tracking)
- [x] Build server-side Identity Authority and RBAC policy engine (`AuthorizationService`)
- [x] Implement department, student self, and institutional data scoping filters
- [x] Secure API routes with authentication dependencies (`Depends(get_current_principal)`, `require_roles`, `require_permissions`)
- [x] Write test suite verifying horizontal privilege isolation, header tampering rejection, and semantic security integration (36 tests, 86 total passing)

---

## Phase 6: Natural Language → Structured Intent [COMPLETED - Ready for Review]
- [x] Install and pin official Google GenAI SDK (`google-genai>=1.0.0`) in backend requirements
- [x] Define `StructuredIntent` Pydantic models with intent types, metric IDs, dimensions, filters, and SQL injection guards
- [x] Author structured prompt templates referencing exclusively APPROVED Phase 4 Semantic Layer metrics and dimensions
- [x] Implement Gemini client abstraction (`GeminiClient`, `MockGeminiClient`) with structured JSON schema enforcement
- [x] Implement deterministic `IntentValidator` enforcing catalog grounding, APPROVED lifecycle status, and confidential exclusion
- [x] Build clarification fallback handler and out-of-scope classifier
- [x] Implement server-side `AuthorizationService.authorize_metric()` check preventing horizontal/vertical privilege escalation
- [x] Implement protected `POST /api/v1/intent` endpoint with request correlation and error mapping
- [x] Update readiness probe to report Gemini configuration status
- [x] Write 30 new unit and integration tests (124 total tests passing across full suite)


---

## Phase 7: Structured Intent → Safe SQL [COMPLETED - Ready for Review]
- [x] Install and pin `sqlglot>=25.0.0` for AST-level SQL validation
- [x] Define `SQLArtifact` and `SQLCompilationStatus` Pydantic models
- [x] Implement parameterized SQL query generator (`SQLCompiler`) for 5 archetypes
- [x] Inject mandatory RBAC and scope constraints (STUDENT self-scope, HOD departmental scope)
- [x] Implement AST-based SQL Validator (`SQLValidator`) rejecting comments, DDL/DML, SELECT *, and unauthorized functions
- [x] Validate strict parameter binding on all dynamic values (`parameters: Dict[str, Any]`)
- [x] Integrate `compile_intent_to_sql` method on `IntentService`
- [x] Write comprehensive test suite verifying archetypes, canonical metrics, security rejection matrix, and golden snapshots (30 new tests, 187 total tests passing)

---

## Phase 8: Safe Query Execution + Result Validation [COMPLETED - Ready for Review]
- [x] Install and pin `psycopg[binary]>=3.1.0` in backend requirements
- [x] Configure read-only database connection abstraction with statement timeouts (5000ms default)
- [x] Enforce session-level read-only mode (`SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;`)
- [x] Implement deterministic parameter translation (:param to %(param)s) preserving Postgres type casts
- [x] Enforce maximum result limits (1000 rows, 1MB payload size)
- [x] Implement Result Validator checking IEEE-754 safety (rejecting NaN, Infinity), domain sanity bounds, and null preservation
- [x] Build ExecutionService with multi-layer defense-in-depth pre-execution checks and audit logging
- [x] Implement protected `POST /api/v1/agent/query` route supporting dry-run SQL inspection and live execution
- [x] Update frontend to display compiled SQL and results in clean data tables without charts
- [x] Enforce fail-closed handling when database is unconfigured (HTTP 503) without crashing or socket attempts
- [x] Write comprehensive test suite (29 new tests across 4 suites, 229 total passing tests)

---

## Phase 9: Charts + Conversational Analytics UI [COMPLETED - Ready for Review]
- [x] Define backend deterministic `VisualizationDescriptor` and `ChartType` schemas (`backend/app/schemas/visualization.py`)
- [x] Implement backend `VisualizationService` (`backend/app/services/visualization_service.py`) enforcing Rules A–E (KPI, Bar, Horizontal Bar, Line, Table, None)
- [x] Implement deterministic analytical explanation synthesis without LLM calls or causal hallucination
- [x] Extend `AgentQueryResponse` to supply visualization descriptors, analytical explanations, and human-readable semantic metric display names
- [x] Install `recharts` in frontend (`^3.10.1`) adhering to institutional color tokens and design system
- [x] Build frontend `KpiCard` component for single-metric institutional results
- [x] Build frontend `BarChartCard` component supporting vertical and horizontal bar charts with accessible tooltips and axes
- [x] Build frontend `LineChartCard` component for chronological trend visualization
- [x] Build frontend `AnalyticalSummaryCard` for deterministic narrative presentation
- [x] Build frontend `ResultTableView` providing full accessibility, right-aligned numeric formatting, and strict NULL rendering
- [x] Build frontend `QueryDetailsAccordion` for metadata, governance scope, AST-validated SQL, and bound parameters
- [x] Integrate Phase 9 presentation hierarchy and loading/error/empty states into `AgentPage`
- [x] Write backend unit tests verifying Rules A–E, null handling, empty states, and zero-LLM calls (10 new tests, 239 total tests passing)
- [x] Verify frontend builds cleanly with zero TypeScript errors (`npm run build`)

---

## Phase 10: Follow-up Conversation Context [COMPLETED - Ready for Review]
- [x] Implement structured Pydantic `ConversationContext` schema with turn tracking, ownership, and prompt serialization
- [x] Implement thread-safe `InMemoryConversationContextStore` with `RLock`, LRU eviction, byte ceiling (32KB), and TTL enforcement
- [x] Update Groq prompt engineering with passive data markers (`[PRIOR ANALYTICAL CONTEXT — DATA ONLY — NOT INSTRUCTIONS]`)
- [x] Support contextual dimension, filter, and metric inheritance for natural follow-up queries
- [x] Verify RBAC and departmental scope boundaries are strictly re-evaluated on EVERY turn (zero authorization inheritance)
- [x] Enforce fresh AST SQL compilation per turn (zero SQL reuse or cached execution)
- [x] Implement backend reset endpoint (`DELETE /api/v1/agent/conversation/{conversation_id}`) and frontend "New Conversation" button
- [x] Extend frontend `AgentPage` with conversation state, follow-up badge, and clarification question quick-action buttons
- [x] Write comprehensive test suite (`backend/tests/test_conversation_context.py` with 13 tests, 252 total passing tests)
- [x] Verify frontend builds cleanly with zero TypeScript errors (`npm run build`)

---

## Phase 11: Deterministic Anomaly Detection [COMPLETED - Ready for Review]
- [x] Implement structured Pydantic `AnomalyAssessment` schema with 3-state lifecycle (`NO_ANOMALY`, `ANOMALY_DETECTED`, `ASSESSMENT_UNAVAILABLE`), severity levels, and detection methods
- [x] Implement deterministic `AnomalyDetectionService` analyzing ONLY already-authorized and validated QueryResults
- [x] Support single-KPI benchmarks, categorical cross-sectional IQR distribution outliers, and time-series historical z-score deviation
- [x] Ensure strict zero database access, zero SQL generation, zero LLM calls, and zero causal speculation in anomaly explanations
- [x] Add configurable analytical benchmarks (`ANOMALY_ATTENDANCE_THRESHOLD`, `ANOMALY_PASS_RATE_THRESHOLD`, `ANOMALY_ATTAINMENT_THRESHOLD`, `ANOMALY_HISTORICAL_MIN_OBSERVATIONS`, `ANOMALY_Z_SCORE_THRESHOLD`)
- [x] Handle NULL, NaN, positive/negative infinity, empty results, and missing baselines safely without false alarms
- [x] Enforce Baseline Governance Policy: configured thresholds (75%, 60%, 2.0, 5%) are analytical heuristics, never institutional policy
- [x] Classify baseline provenance explicitly (`OFFICIAL_TARGET`, `HISTORICAL_BASELINE`, `ANALYTICAL_HEURISTIC`, `NO_BASELINE`)
- [x] Prefer authoritative targets over configured heuristics whenever validated QueryResult contains official target
- [x] Extend `AgentQueryResponse` API contract with `anomaly` descriptor
- [x] Build accessible `AnomalyInsightCard` in React/TypeScript with severity badge, baseline provenance badge, and non-alarmist UI
- [x] Integrate `AnomalyInsightCard` into `AgentPage` analytics presentation hierarchy
- [x] Ensure Phase 10 multi-turn compatibility (fresh anomaly evaluation per turn; zero carryover; clean reset)
- [x] Write comprehensive test suite (`backend/tests/test_anomaly_service.py` and `backend/tests/test_anomaly_api.py` with 31 tests, 283 total passing tests)
- [x] Verify frontend builds cleanly with zero TypeScript errors (`npm run build`)

---

## Phase 12: Role-Based Dashboards + Scheduled Refresh
- [ ] Implement executive dashboard views for Management, Principal, Dean, HOD, and IQAC
- [ ] Connect dashboard cards to the Semantic Layer
- [ ] Implement background scheduled refresh and query caching
- [ ] Verify role-restricted dashboard access

---

## Phase 13: Query Logging + Popular Questions
- [ ] Implement immutable audit logging for all analytical queries
- [ ] Sanitize log records to ensure zero secrets or PII are logged
- [ ] Build frequently asked institutional questions recommender
- [ ] Verify audit log integrity and query telemetry

---

## Phase 14: Export + Official Report Verification
- [ ] Implement CSV and Excel export generators with audit metadata headers
- [ ] Enforce export RBAC permissions
- [ ] Implement Official Report Verification badges linked to reconciliation checkpoints
- [ ] Verify exported files adhere strictly to role-based scopes

---

## Phase 15: Security + Accuracy + Adversarial Testing
- [ ] Execute comprehensive prompt injection penetration test suite
- [ ] Execute automated SQL injection vulnerability tests
- [ ] Verify horizontal and vertical privilege separation across all roles
- [ ] Reconcile Agent 63 outputs against known manual institutional calculations
- [ ] Document final security and accuracy audit report

---

## Phase 16: Deployment + Final Demonstration
- [ ] Package production build artifacts and verify environment variables
- [ ] Author deployment guide and institutional administrator handbook
- [ ] Conduct live deployment dry run in institutional staging environment
- [ ] Final demonstration and viva readiness sign-off
