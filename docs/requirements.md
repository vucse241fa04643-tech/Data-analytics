# Agent 63 – System Requirements Specification (SRS)

> **Document Version:** 1.0.0  
> **Status:** Baseline Established (Phase 0)  
> **Traceability:** Aligned with Master Architecture and 17-Phase Development Plan

---

## A. Functional Requirements
- **FR-01 [Future - Phase 6]:** The system shall accept natural-language analytical questions from authenticated users via a clean institutional web interface.
- **FR-02 [Future - Phase 8]:** The system shall transform validated analytical intents into accurate numerical answers and tabular records sourced exclusively from the college-provided database.
- **FR-03 [Future - Phase 9]:** The system shall display verified results in dedicated institutional Result Cards containing metric values, formula explanations, population filters, time periods, and assumptions.
- **FR-04 [Future - Phase 9]:** The system shall automatically select and render visual charts (e.g., bar, line, KPI, distribution) corresponding to the query dimensions.
- **FR-05 [Future - Phase 10]:** The system shall support multi-turn conversational follow-ups (e.g., "What about 2024?") preserving prior scope and filters unless overridden.

---

## B. Analytics Requirements
- **AR-01 [IMPLEMENTED - Phase 4]:** Analytics calculations adhere strictly to predefined institutional formulas defined in the Semantic Layer (`semantic_layer/registry/semantic_registry.json`).
- **AR-02 [Future - Phase 8]:** The system must support fundamental academic aggregations: counts, percentages, averages, medians, year-over-year comparisons, and cohort distributions.
- **AR-03 [Future - Phase 8]:** Null values, incomplete semester records, and inactive student statuses must be handled deterministically as specified by metric rules.
- **AR-04 [Future - Phase 8]:** Calculations must prevent division-by-zero errors and flag zero-denominator scenarios gracefully.

---

## C. Semantic Layer Requirements (Phase 4 - Implemented)
- **SR-01 [IMPLEMENTED - Phase 4]:** The Semantic Layer acts as the single authoritative source of truth for metric definitions, dimensions, filters, and join paths (`semantic_layer/`).
- **SR-02 [IMPLEMENTED - Phase 4]:** Each metric defines: Unique Metric ID, Canonical Name, Description, Domain, Calculation Formula, Aggregation, Source Tables, Source Columns, Time Semantics, Null Handling, Sensitivity, Status, and Provenance.
- **SR-03 [IMPLEMENTED - Phase 4]:** The semantic model is version-controlled and human-auditable in JSON format with an automated validator (`scripts/validate_semantic_layer.py`).
- **SR-04 [IMPLEMENTED - Phase 4]:** An LLM is strictly forbidden from formulating or altering a metric definition or join at runtime; queries must resolve to registered metric IDs.

---

## D. Security Requirements
- **SEC-01 [Phase 0 / Ongoing]:** Credentials, private keys, API secrets, and connection strings must never be committed to source control or exposed in client bundles.
- **SEC-02 [IMPLEMENTED - Phase 2]:** All backend API endpoints enforce CORS policies restricted to authorized institutional domains.
- **SEC-03 [Future - Phase 7]:** The LLM must have zero direct network or credential access to the database.
- **SEC-04 [Future - Phase 8]:** Database execution must utilize dedicated least-privilege read-only accounts.
- **SEC-05 [Future - Phase 6]:** The system must implement robust prompt-injection safeguards to prevent prompt leaking or malicious semantic manipulation.
- **SEC-06 [IMPLEMENTED - Phase 2]:** Backend must never expose endpoints capable of arbitrary SQL execution (`POST /execute-sql`, raw queries).
- **SEC-07 [IMPLEMENTED - Phase 2]:** Application errors must return sanitized JSON envelopes without exposing Python stack traces, database credentials, or internal filesystem paths.

---

## E. Backend Foundation Requirements (Phase 2 - Implemented)
- **BER-01 [IMPLEMENTED - Phase 2]:** The backend must provide a clean, modular FastAPI application structure with decoupled router architecture.
- **BER-02 [IMPLEMENTED - Phase 2]:** API endpoints must reside under a versioned namespace (e.g. `/api/v1/health`).
- **BER-03 [IMPLEMENTED - Phase 2]:** Configuration must be centralized via Pydantic Settings with validated environment variable loading and safe defaults.
- **BER-04 [IMPLEMENTED - Phase 2]:** The application must initialize and pass tests completely without requiring a live PostgreSQL installation or connection.
- **BER-05 [IMPLEMENTED - Phase 2]:** System telemetry must use structured JSON logging, scrubbing sensitive tokens, passwords, and PII.
- **BER-06 [IMPLEMENTED - Phase 2]:** Every request must be tagged with a validated correlation ID (`X-Request-ID`) returned in headers and embedded in logs.
- **BER-07 [IMPLEMENTED - Phase 2]:** Centralized exception handlers must trap domain and HTTP exceptions, returning consistent `{ "error": { "code", "message", "request_id" } }` envelopes.
- **BER-08 [IMPLEMENTED - Phase 2]:** The system must implement distinct `/api/v1/health` (liveness) and `/api/v1/health/ready` (readiness) endpoints, explicitly reporting when the college database is unconfigured.
- **BER-09 [IMPLEMENTED - Phase 2]:** The backend must load and validate the authoritative Phase 1 Schema Registry (`agent63_schema_registry.json`) for internal metadata lookups without exposing public discovery endpoints.
- **BER-10 [IMPLEMENTED - Phase 2]:** The database layer must provide an isolated abstraction layer without exposing arbitrary SQL execution methods.

---

## E. Authentication Requirements
- **AUT-01 [IMPLEMENTED - Phase 5]:** The system implements a production-oriented Authentication + RBAC foundation authenticating institutional users via Argon2id hashed credentials against the `identity.*` schema abstraction. (Actual production authentication requires the future college identity database integration; unconfigured production runtime fails closed).
- **AUT-02 [IMPLEMENTED - Phase 5]:** Authenticated sessions issue cryptographically signed JWT tokens with strictly minimal claims (`sub`, `jti`, `iat`, `nbf`, `exp`, `iss`, `aud`), configurable expiry (default 60 min), and token revocation abstraction via JTI tracking (in-memory for process lifetime; persistent store to be backed by database/cache in a future phase).
- **AUT-03 [IMPLEMENTED - Phase 5]:** Passwords are cryptographically hashed and verified using Argon2id (`argon2-cffi`). Passwords and hashes are strictly excluded from logs.

---

## F. Role-Based Access Control (RBAC) Requirements
- **RBC-01 [IMPLEMENTED - Phase 5]:** The system supports institutional roles derived from the college schema: `STUDENT`, `FACULTY`, `MENTOR`, `HOD`, `DEAN`, `COE`, `IQAC`, `PLACEMENT`, `ACCOUNTS`, `COUNSELLOR`, `PRINCIPAL`, and `ADMIN`.
- **RBC-02 [IMPLEMENTED - Phase 5]:** Scoped authorization is enforced as `authenticated principal -> role -> permission -> scope -> semantic sensitivity -> authorization decision`:
  - `HOD`: Restricted exclusively to their assigned academic department (e.g., `DEPARTMENT:CSE`).
  - `DEAN`: Restricted to their assigned academic school/faculty.
  - `STUDENT`: Restricted to `SELF` scope (`student_id`).
  - `PRINCIPAL` & `IQAC`: Institutional-wide scope across non-confidential domains.
  - Role claims in JWT are non-authoritative; permissions and scopes are dynamically resolved server-side on every request.
- **RBC-03 [IMPLEMENTED - Phase 5]:** Client-side visibility flags, client-provided headers, and token payload tampering are strictly non-authoritative; all authorization is evaluated server-side.

---

## G. Database Requirements
- **DB-01 [Phase 0 / Phase 1 - Completed]:** The authoritative data source is the college-provided PostgreSQL 14+ database (`01_foundation.sql` / `schema_full.sql`). Zero synthetic university databases or mock tables were created.
- **DB-02 [Phase 1 - Completed]:** Database engine verified as PostgreSQL 14+ with pgcrypto and pg_trgm extensions across 21 institutional schemas.
- **DB-03 [Phase 1 - Completed]:** Maintained machine-readable Schema Registry (`database/mappings/agent63_schema_registry.json`) and complete inventory (`database/schema/college_schema_inventory.json`) capturing 225 tables, 11 views, foreign keys, and 7 RLS-enabled tables.
- **DB-04 [Phase 1 - Completed]:** All schema objects classified across 5 sensitivity tiers: `PUBLIC_ANALYTICS`, `INTERNAL_ANALYTICS`, `ROLE_RESTRICTED`, `SENSITIVE`, and `HIGHLY_SENSITIVE`.
- **DB-05 [Phase 1 - Completed]:** Strict isolation of the `confidential` schema (medical/counselling records) and exam security objects (`assessment.question_paper`) with non-negotiable `DENY_GENERAL_ANALYTICS` status.
- **DB-06 [Phase 1 - Completed]:** Documented read-only connection scaffolding with least privilege and 5,000ms query timeout limit (`database/documentation/read-only-integration.md`).
- **DB-07 [Phase 1 / Future - Phase 8]:** The system shall never modify, rename, truncate, or alter the college database structure or data. Real student data access remains unconfigured in Phase 1.

---

## H. Natural Language Understanding Requirements
- **NLR-01 [IMPLEMENTED - Phase 6]:** The Natural Language engine parses unstructured text into a validated `StructuredIntent` JSON object using Google Gemini (`google-genai` SDK) grounded exclusively in the Phase 4 Semantic Layer.
- **NLR-02 [IMPLEMENTED - Phase 6]:** The parser extracts: Intent Type, Primary/Secondary Metrics, Dimensional Groupings, Structured Filters, Time Context (academic year, term), and Reasoning Summary.
- **NLR-03 [IMPLEMENTED - Phase 6]:** Ambiguous questions, missing metrics, or out-of-scope prompts trigger explicit clarification requests or out-of-scope statuses rather than generating speculative interpretations.
- **NLR-04 [IMPLEMENTED - Phase 6]:** Zero SQL generation, execution, or raw SQL clauses are permitted; all filters are strictly validated against SQL keywords.
- **NLR-05 [IMPLEMENTED - Phase 6]:** Server-side authorization evaluates all extracted intents against authenticated principal roles and scopes prior to acceptance.

---

## I. SQL Safety Requirements
- **SQL-01 [Future - Phase 7]:** Only read-only `SELECT` queries may be constructed.
- **SQL-02 [Future - Phase 7]:** The SQL Validator must parse query ASTs and immediately reject statements containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE`, or `EXEC`.
- **SQL-03 [Future - Phase 7]:** All dynamic user filter values must be bound via parameterized inputs to eliminate SQL injection vulnerabilities.
- **SQL-04 [Future - Phase 8]:** Database queries must have an enforced timeout (default: 5,000ms) to prevent Denial of Service or runaway queries.

---

## J. Visualization Requirements
- **VIS-01 [Future - Phase 9]:** Frontend visual charts must be rendered using Recharts adhering strictly to the institutional color palette.
- **VIS-02 [Future - Phase 9]:** Visualizations must be generated from backend data specifications; no arbitrary executable JavaScript code may be generated by the LLM.
- **VIS-03 [Future - Phase 9]:** Standard chart mappings:
  - Single Metric / KPI $\rightarrow$ Institutional Stat Card
  - Temporal Trends $\rightarrow$ Clean Line Chart
  - Cohort / Departmental Comparisons $\rightarrow$ Rounded Bar Chart
  - Distribution $\rightarrow$ Histogram / Categorical Breakdown
  - Detailed Records $\rightarrow$ Paginated Institutional Table

---

## K. Conversation Context Requirements
- **CCR-01 [Future - Phase 10]:** The system shall maintain structured conversational state (active metric, department, period, cohort) across multi-turn exchanges.
- **CCR-02 [Future - Phase 10]:** Conversational context must never override or loosen user RBAC boundaries.
- **CCR-03 [Future - Phase 10]:** Users must be able to clear or reset conversational context at any time.

---

## L. Anomaly Detection Requirements
- **ADR-01 [Future - Phase 11]:** The anomaly engine shall compute explainable statistical metrics (percentage changes, moving averages, standard deviation thresholds).
- **ADR-02 [Future - Phase 11]:** Anomalies must present observed values, historical baselines, calculated deviation, and severity tags without hallucinating causal claims.

---

## M. Dashboard Requirements
- **DBR-01 [Future - Phase 12]:** The system shall provide role-tailored dashboard views for Management, Principal, Dean, HOD, and IQAC.
- **DBR-02 [Future - Phase 12]:** Dashboards must consume the same verified semantic metric layer as the conversational interface.
- **DBR-03 [Future - Phase 12]:** Dashboard data must support scheduled caching to ensure instantaneous load times.

---

## N. Logging & Audit Requirements
- **LOG-01 [Future - Phase 13]:** The system shall maintain an immutable audit log recording: Timestamp, User ID, Role, Question Category, Metric ID, Parameter Hash, Execution Duration, and Status.
- **LOG-02 [Phase 0 / Ongoing]:** Audit logs and application logs must strictly scrub passwords, tokens, API keys, and sensitive student identifiers.

---

## O. Export Requirements
- **EXP-01 [Future - Phase 14]:** Authorized users shall be permitted to export verified result datasets to CSV and Excel.
- **EXP-02 [Future - Phase 14]:** Export files must include header metadata: Generated Date, Requesting User, Metric Definition, Scope, and Verification Status.
- **EXP-03 [Future - Phase 14]:** Export capabilities must be governed by role-specific export permissions.

---

## P. Official Report Verification Requirements
- **ORV-01 [Future - Phase 14]:** The system must explicitly distinguish between `AD-HOC ANALYTICS` and `OFFICIAL VERIFIED INSTITUTIONAL FIGURE`.
- **ORV-02 [Future - Phase 14]:** Official institutional figures must reference reconciliation checkpoints against approved statutory reports (e.g., AISHE, NAAC SSR).

---

## Q. Testing Requirements
- **TST-01 [Phase 0]:** Base repository sanity, folder structure verification, and credential checks.
- **TST-02 [Future - Phase 2+]:** 100% test coverage for security barriers, AST validators, and RBAC policy evaluation.
- **TST-03 [Future - Phase 15]:** Comprehensive adversarial test suites covering SQL injection, prompt injection, and semantic boundary bypass attempts.

---

## R. Deployment Requirements
- **DEP-01 [Future - Phase 16]:** The system shall be deployable in an on-premises college server environment or institutional private cloud.
- **DEP-02 [Future - Phase 16]:** Configuration must be completely externalized via environment variables.
