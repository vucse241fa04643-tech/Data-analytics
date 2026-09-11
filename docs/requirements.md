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
- **AR-01 [Future - Phase 4]:** Analytics calculations must adhere strictly to predefined institutional formulas defined in the Semantic Layer.
- **AR-02 [Future - Phase 8]:** The system must support fundamental academic aggregations: counts, percentages, averages, medians, year-over-year comparisons, and cohort distributions.
- **AR-03 [Future - Phase 8]:** Null values, incomplete semester records, and inactive student statuses must be handled deterministically as specified by metric rules.
- **AR-04 [Future - Phase 8]:** Calculations must prevent division-by-zero errors and flag zero-denominator scenarios gracefully.

---

## C. Semantic Layer Requirements
- **SR-01 [Future - Phase 4]:** The Semantic Layer shall act as the single authoritative source of truth for metric definitions, dimensions, filters, and join paths.
- **SR-02 [Future - Phase 4]:** Each metric must define: Unique Metric ID, Formal Name, Description, Calculation Formula, Required Tables, Filter Clauses, Supported Time Granularities, and Allowed Dimensions.
- **SR-03 [Future - Phase 4]:** The semantic model must be version-controlled and human-auditable.
- **SR-04 [Future - Phase 4]:** An LLM must never be allowed to formulate or alter a metric definition at runtime.

---

## D. Security Requirements
- **SEC-01 [Phase 0 / Ongoing]:** Credentials, private keys, API secrets, and connection strings must never be committed to source control or exposed in client bundles.
- **SEC-02 [Future - Phase 2]:** All backend API endpoints must enforce strict TLS/HTTPS and CORS policies restricted to authorized institutional domains.
- **SEC-03 [Future - Phase 7]:** The LLM must have zero direct network or credential access to the database.
- **SEC-04 [Future - Phase 8]:** Database execution must utilize dedicated least-privilege read-only accounts.
- **SEC-05 [Future - Phase 6]:** The system must implement robust prompt-injection safeguards to prevent prompt leaking or malicious semantic manipulation.

---

## E. Authentication Requirements
- **AUT-01 [Future - Phase 5]:** The system shall authenticate institutional users via secure username/password or institutional SSO integration.
- **AUT-02 [Future - Phase 5]:** Authenticated sessions must issue cryptographically signed JWT tokens with configurable expiration (default 60 minutes).
- **AUT-03 [Future - Phase 5]:** Passwords must be hashed using industry-standard adaptive hashing (bcrypt/argon2).

---

## F. Role-Based Access Control (RBAC) Requirements
- **RBC-01 [Future - Phase 5]:** The system shall support distinct institutional roles: `MANAGEMENT`, `PRINCIPAL`, `DEAN`, `HOD`, and `IQAC`.
- **RBC-02 [Future - Phase 5]:** Role-based scoping must be enforced at the backend service layer before query generation:
  - `HOD`: Restricted exclusively to data from their assigned academic department.
  - `DEAN`: Restricted to departments and programs within their assigned academic school.
  - `PRINCIPAL` & `MANAGEMENT`: Access to institution-wide aggregated metrics.
  - `IQAC`: Access to institutional quality, compliance, and accreditation indicators.
- **RBC-03 [Future - Phase 5]:** Client-side visibility flags must never be considered security boundaries; permissions must be validated on every API call.

---

## G. Database Requirements
- **DB-01 [Phase 0 / Phase 1]:** The authoritative data source is the college-provided database. No synthetic university database or mock tables shall be created.
- **DB-02 [Phase 0 / Phase 1]:** The system must not assume any specific database engine (PostgreSQL, MySQL, SQL Server, Oracle) until Phase 1 inspection is complete.
- **DB-03 [Future - Phase 1]:** The system shall maintain an inspected Schema Registry capturing actual table names, column types, primary keys, foreign keys, and indexes.
- **DB-04 [Future - Phase 1/8]:** The system shall never modify, rename, truncate, or alter the college database structure or data.

---

## H. Natural Language Requirements
- **NLR-01 [Future - Phase 6]:** The Natural Language engine shall parse unstructured text into a validated `IntentSchema` JSON object.
- **NLR-02 [Future - Phase 6]:** The parser must extract: Target Metric, Population/Entity, Academic Period, Dimensional Groupings, and Explicit Filters.
- **NLR-03 [Future - Phase 6]:** Ambiguous questions must trigger an explicit clarification request rather than generating a speculative query.

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
