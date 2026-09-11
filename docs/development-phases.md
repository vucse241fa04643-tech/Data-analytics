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
- **Objective:** Inspect the authoritative college-provided database, document its real schema, and build a controlled schema registry without mutating the database.
- **Major Tasks:**
  - Connect in read-only inspection mode to the college database.
  - Determine database engine (PostgreSQL, MySQL, SQL Server, etc.), version, and collation.
  - Catalog all existing tables, columns, data types, primary keys, foreign keys, and indexes.
  - Document domain models (e.g., student records, attendance, marks, courses, faculty).
  - Create the Schema Registry in `database/schema/` and document mappings in `database/mappings/`.
  - Identify data quality quirks, nullable columns, and edge cases.
- **Expected Deliverables:** Database inspection report (`database/documentation/`), Schema Registry files, logical-to-physical field mappings.
- **Acceptance Criteria:** Zero modifications/writes to college database; no synthetic university tables created; schema registry accurately mirrors real database.
- **Dependencies:** Phase 0.

---

## Phase 2: FastAPI Backend Foundation
- **Objective:** Establish a robust, production-grade FastAPI application structure with configuration management, health endpoints, and modular routing.
- **Major Tasks:**
  - Set up Python virtual environment and core dependencies (`fastapi`, `uvicorn`, `pydantic-settings`).
  - Implement modular backend directory structure (`app/api/`, `app/core/`, `app/schemas/`).
  - Create health check endpoints (`/api/v1/health`, `/api/v1/ready`).
  - Configure CORS middleware, centralized exception handling, and structured request logging.
  - Add backend test harness with `pytest`.
- **Expected Deliverables:** Running FastAPI server, health check endpoints, configuration loader, base test suite.
- **Acceptance Criteria:** Server starts cleanly; health check returns `200 OK`; test suite passes.
- **Dependencies:** Phase 0, Phase 1.

---

## Phase 3: React Frontend + Institutional UI
- **Objective:** Build the institutional frontend application using React and Vite, implementing the institutional visual design system.
- **Major Tasks:**
  - Initialize Vite React project with strict Vanilla CSS architecture and design tokens.
  - Build Institutional Header with college logo area, project identity, and accreditation badges.
  - Implement 3-column desktop layout (Navigation sidebar, Central Workspace, Insights panel).
  - Build institutional status bar, theme tokens, and responsive layout wrappers.
  - Render clean placeholders for official logos adhering to branding guidelines.
- **Expected Deliverables:** Functional React + Vite frontend adhering to institutional design language.
- **Acceptance Criteria:** Frontend builds without errors; visual styling matches the institutional reference; responsive layout functional.
- **Dependencies:** Phase 0, Phase 2.

---

## Phase 4: Semantic Layer + Metric Catalog
- **Objective:** Define institutional business metrics, formulas, aggregations, and dimensions in a version-controlled semantic catalog.
- **Major Tasks:**
  - Define core institutional metrics (e.g., attendance percentage, pass percentage, student strength) based on inspected Phase 1 schema.
  - Specify mathematical formulas, required joins, dimension mappings, and null-handling logic.
  - Implement Pydantic models for metric definitions in `semantic_layer/metrics/`.
  - Build catalog query engine to look up metrics by name or alias.
- **Expected Deliverables:** Metric catalog files, data dictionary, metric resolution service.
- **Acceptance Criteria:** Every metric has an unambiguous formula linked to real college columns; unit tests validate catalog lookups.
- **Dependencies:** Phase 1, Phase 2.

---

## Phase 5: Authentication + RBAC
- **Objective:** Implement secure institutional authentication and fine-grained role-based access control.
- **Major Tasks:**
  - Implement JWT token generation and validation services.
  - Define role permissions matrix (`MANAGEMENT`, `PRINCIPAL`, `DEAN`, `HOD`, `IQAC`).
  - Implement role-based data scoping (e.g., department boundary enforcement for HOD).
  - Secure API routes with FastAPI dependency injection (`Depends(get_current_user)`).
- **Expected Deliverables:** Auth router (`/api/v1/auth/login`), JWT middleware, RBAC enforcement engine, security unit tests.
- **Acceptance Criteria:** Unauthorized requests rejected with `401`/`403`; department scoping strictly prevents horizontal privilege escalation.
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
