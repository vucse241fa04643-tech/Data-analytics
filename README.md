# Agent 63 – Data Analytics Agent

> **Enterprise-Grade Conversational Institutional Analytics System**  
> *Transforming natural-language institutional queries into verified, role-governed data insights without direct or unrestricted LLM database exposure.*

---

## 1. Project Overview
**Agent 63 – Data Analytics Agent** is an institutional data intelligence platform designed specifically for academic institutions. It bridges the gap between institutional decision-makers and complex institutional databases by enabling natural-language questioning while upholding strict institutional data governance, deterministic query validation, row-level access control, and mathematical result verification.

Unlike generic chatbot wrappers or text-to-SQL toys, Agent 63 implements a controlled multi-stage analytics pipeline. Questions flow through semantic resolution, role-based scope enforcement, approved schema mapping, and read-only query execution before being translated into clear institutional result cards, visualizations, and auditable metrics.

---

## 2. Project Purpose
The primary purpose of Agent 63 is to empower educational leadership with instantaneous, accurate, and context-rich analytics on institutional performance. When a user asks:
> *"What is the average attendance of CSE students in 2025?"*

The system does not merely generate a raw number or an uncontrolled SQL statement. Instead, it provides:
- **Verified Numerical Result** (e.g., `82.6%`)
- **Metric Definition & Formula** (how attendance percentage is calculated)
- **Time Period & Cohort** (`2025 Academic Year`)
- **Population & Scope** (`CSE Department Enrolled Students`)
- **Active Filters & Constraints** (`Status = Active`, `Dept = CSE`)
- **Underlying Assumptions & Edge Cases** (handling of medical leaves, electives)
- **Interactive Visualizations** (trend over time, comparison charts via Recharts)
- **Verification Status** (distinguishing between ad-hoc exploratory analytics and official validated reports)

---

## 3. Target Institutional Users
The system is tailored for key administrative and academic leadership roles:
- **Management / Governing Body**: Institution-wide high-level KPIs, multi-year trends, enrollment statistics, accreditation health.
- **Principal**: Institution-wide academic performance, overall pass percentages, departmental benchmarks, cross-departmental attendance.
- **Dean**: School-level performance metrics, academic progress, faculty ratios, program evaluations within assigned schools.
- **Head of Department (HOD)**: Department-specific drill-downs, section attendance, subject-wise pass rates, faculty allocation, internal marks.
- **Internal Quality Assurance Cell (IQAC)**: Institutional accreditation metrics (NAAC, NBA, NIRF), continuous quality indicators, anomaly detection, compliance auditing.

---

## 4. Core Problem Being Solved
Educational institutions face significant data bottlenecks:
1. **Siloed and Inaccessible Data**: Management relies on busy IT/ERP staff to write ad-hoc queries, causing delays of days or weeks for basic analytics.
2. **Hallucination & AI Insecurity**: Directly connecting an LLM to a database risks SQL injection, data exfiltration, hallucinated calculations, or unauthorized access across departments.
3. **Ambiguity in Definitions**: Different departments define metrics differently (e.g., "attendance" with vs. without lab sessions).
4. **Lack of Trust in Ad-Hoc Numbers**: Unverified figures presented in meetings often conflict with official institutional compliance reports.

Agent 63 resolves these challenges by introducing a deterministic **Semantic Layer** and a **Safe SQL Pipeline** that guarantees mathematical accuracy, strict RBAC, and contextual transparency.

---

## 5. High-Level Architecture
Agent 63 enforces complete separation between user input, natural-language reasoning, and database execution:

```
USER
  ↓
AGENT 63 INSTITUTIONAL WEB INTERFACE
  ↓
REACT + VITE FRONTEND (Tailored Institutional UI)
  ↓
FASTAPI BACKEND (REST / WebSocket API Gateway)
  ↓
AUTHENTICATION (JWT / Institutional Identity)
  ↓
RBAC / AUTHORIZATION ENGINE (Role & Scope Verification)
  ↓
AGENT 63 ORCHESTRATOR
  ↓
SEMANTIC LAYER & METRIC CATALOG
  ↓
STRUCTURED INTENT (Validated JSON Intent Object)
  ↓
AUTHORIZED DATA SCOPE (Row-Level Department & Metric Filter Enforcement)
  ↓
COLLEGE DATABASE SCHEMA REGISTRY (Controlled Physical Schema Mapping)
  ↓
SAFE SQL GENERATION (Read-Only, Parameterized SQL Construction)
  ↓
SQL VALIDATOR (AST Parser: Denies INSERT/UPDATE/DELETE/ALTER/DROP)
  ↓
READ-ONLY QUERY EXECUTOR (Isolated Read-Only DB Connection)
  ↓
COLLEGE-PROVIDED DATABASE(S) (Production Institutional Storage)
  ↓
RESULT VALIDATION (Type, Boundary, Null, and Aggregation Checking)
  ↓
ANALYTICS & ANOMALY DETECTION ENGINE
  ↓
VISUALIZATION SPECIFICATION (Recharts Formats)
  ↓
EXPLANATION & AUDIT LOGGING
  ↓
INSTITUTIONAL UI RESULT CARD
  ↓
USER
```

---

## 6. Technology Direction
- **Frontend**: React 18+, Vite, Recharts, Vanilla CSS / Centralized Design Tokens (Strictly institutional visual language; no generic Tailwind/ChatGPT clones).
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (Core/ORM compatible with inspected college database).
- **Security & RBAC**: JWT Bearer authentication, fine-grained role-based access control, cryptographic query hashing, read-only isolated database credentials.
- **Semantic & Orchestration**: Controlled domain-specific metric catalog, Pydantic-based structured intent parsing, AST SQL validation.
- **Storage & Infrastructure**: College-provided relational database, environment-isolated configuration.

---

## 7. College Database Strategy
> [!IMPORTANT]
> **THE COLLEGE HAS ALREADY PROVIDED THE DATABASE / DATABASES.**

1. **NO Replacement Database**: The development team will NEVER create a synthetic university database or invent replacement tables.
2. **NO Assumed Database Engine**: The system does not presuppose PostgreSQL, MySQL, SQL Server, or Oracle. The actual engine, schema, constraints, and character sets will be formally inspected during **Phase 1**.
3. **NO Database Mutations**: The college database will never be restructured, renamed, altered, or populated with fake institutional records.
4. **Read-Only Integration**: All analytical queries will execute strictly via read-only database roles with zero write/DDL privileges.

---

## 8. UI & Branding Direction
The visual identity is anchored directly to the provided institutional reference image:
- **Surfaces**: Crisp white cards (`#FFFFFF`) on a subtle, clean light-blue workspace background (`#F4F7FB` to `#EDF2F7`).
- **Typography**: Professional dark navy headings (`#0F172A` / `#1E293B`) with high legibility.
- **Accents**: Restrained institutional deep blues and subtle borders, avoiding gaudy neon or dark cyberpunk themes.
- **Layout**: Structured desktop-first dashboard featuring:
  - Top institutional header containing College crest, Department/Agent 63 identity, and Accreditation badges.
  - Left-hand collapsible navigation.
  - Central analytics workspace with query input and structured result cards.
  - Right-hand contextual insights and metric definitions panel.
  - Bottom institutional system status bar.
- **Official Logos**: Logos must be authentic assets provided by the college. **No fake or CSS-generated logos are permitted.**

---

## 9. Security Philosophy
Security in Agent 63 is non-negotiable and follows defense-in-depth:
- **Zero LLM Database Credentials**: The language model is never provided database connection strings or passwords.
- **Pre-Execution Authorization**: Role-based access control (RBAC) and department scope filters are injected in backend code *before* SQL generation.
- **SQL AST Validation**: Any query containing mutation keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, administrative commands) is rejected immediately.
- **Result & Bounds Checking**: Impossible numbers (e.g., negative attendance or marks > 100%) are trapped by result validators before rendering.
- **Audit Logging**: Every query, user role, metric accessed, and execution time is securely logged without capturing sensitive passwords or secrets.

---

## 10. Development Methodology & Phase Discipline
To guarantee rock-solid stability and verifiable correctness, Agent 63 is developed strictly according to a **17-Phase Progressive Roadmap (Phases 0 through 16)**.
- Each phase has defined objectives, deliverables, and acceptance criteria.
- **Strict Rule**: No phase may be started until the preceding phase is verified, tested, and approved.
- Premature feature development (e.g., building UI before backend, or SQL generation before schema inspection) is strictly forbidden.

---

## 11. Complete Phase Roadmap

| Phase | Title | Focus Area | Status |
| :---: | :--- | :--- | :---: |
| **Phase 0** | **Project Foundation + Architecture + Design System** | **Docs, directory structure, branding setup, git safety** | **COMPLETED** |
| Phase 1 | College Database Inspection + Safe Integration + Schema Mapping | Inspect engine, map real tables/columns, build schema registry | *PLANNED* |
| Phase 2 | FastAPI Backend Foundation | FastAPI application structure, API routers, health checks | *PLANNED* |
| Phase 3 | React Frontend + Institutional UI | Institutional layout, header, branding, navigation, CSS tokens | *PLANNED* |
| Phase 4 | Semantic Layer + Metric Catalog | Metric formulas, dimensions, aggregations, data dictionary | *PLANNED* |
| Phase 5 | Authentication + RBAC | JWT auth, role definitions, department data scoping | *PLANNED* |
| Phase 6 | Natural Language → Structured Intent | Prompt engineering, intent extraction, Pydantic schema validation | *PLANNED* |
| Phase 7 | Structured Intent → Safe SQL | Intent-to-SQL translation, parameterization, SQL AST validation | *PLANNED* |
| Phase 8 | Safe Query Execution + Result Validation | Read-only executor, type checking, bounds validation | *PLANNED* |
| Phase 9 | Charts + Conversational Analytics UI | Recharts rendering, result cards, interpretation panel | *PLANNED* |
| Phase 10 | Follow-up Conversation Context | Multi-turn memory, context inheritance, filter chaining | *PLANNED* |
| Phase 11 | Anomaly Detection | Statistical baselines, moving averages, standard deviation alerts | *PLANNED* |
| Phase 12 | Role-Based Dashboards + Scheduled Refresh | Management/Principal/HOD dashboards, automated caching | *PLANNED* |
| Phase 13 | Query Logging + Popular Questions | Audit logging, telemetry, frequently asked institutional questions | *PLANNED* |
| Phase 14 | Export + Official Report Verification | CSV/Excel generation, reconciliation against official reports | *PLANNED* |
| Phase 15 | Security + Accuracy + Adversarial Testing | Prompt injection testing, SQL injection testing, accuracy audit | *PLANNED* |
| Phase 16 | Deployment + Final Demonstration | Production build, environment validation, viva demonstration | *PLANNED* |

---

## 12. Current Implementation Status

### [x] IMPLEMENTED IN PHASE 0
- Project architecture and directory structure established.
- Comprehensive technical documentation (`docs/architecture.md`, `docs/requirements.md`, `docs/security.md`, `docs/development-phases.md`, `docs/development-checklist.md`, `docs/ui-design.md`).
- Environment variable strategy and template (`.env.example`) with zero exposed secrets.
- Hardened `.gitignore` covering Python, Node.js, credentials, and OS caches.
- Institutional branding directory structure (`frontend/public/assets/branding/`) and asset guidelines.
- UI design tokens and component specification documented.
- Git repository sanity and security verification checks executed.

### [ ] PLANNED FOR FUTURE PHASES (NOT IMPLEMENTED IN PHASE 0)
- Database connections or queries (*Phase 1*)
- Synthetic database schemas or mock tables (*Strictly Prohibited*)
- FastAPI backend routes or services (*Phase 2*)
- React / Vite frontend code (*Phase 3*)
- Semantic layer & metric catalog (*Phase 4*)
- Authentication & RBAC engine (*Phase 5*)
- Natural language intent parsing or LLM calls (*Phase 6*)
- SQL generation & query executor (*Phases 7 & 8*)
- Dashboards, charts, anomaly detection, exports (*Phases 9–14*)

---

## 13. Repository Structure

```
Data-analytics/
├── .gitignore                          # Git ignore configuration
├── .env.example                        # Template environment variables
├── README.md                           # Master project documentation
│
├── docs/                               # System Architectural Documentation
│   ├── architecture.md                 # End-to-end component flow & boundaries
│   ├── requirements.md                 # Comprehensive functional & non-functional requirements
│   ├── security.md                     # Security policies, RBAC, SQL safety rules
│   ├── development-phases.md           # 17-Phase development specification
│   ├── development-checklist.md        # Master phase-by-phase acceptance checklist
│   └── ui-design.md                    # Institutional UI/UX specification & design tokens
│
├── frontend/                           # React + Vite Client Application (Phase 3+)
│   └── public/
│       └── assets/
│           └── branding/               # Official college logos & crests directory
│               ├── README.md           # Branding asset specifications
│               └── .gitkeep
│
├── backend/                            # FastAPI Server Application (Phase 2+)
│   └── .gitkeep
│
├── semantic_layer/                     # Metric Catalog & Dimensions (Phase 4+)
│   └── .gitkeep
│
├── database/                           # College Database Registry & Mappings (Phase 1+)
│   ├── schema/                         # Discovered schema definitions
│   ├── mappings/                       # Logical-to-physical field mappings
│   └── documentation/                  # Database inspection reports
│
├── analytics/                          # Statistical & Anomaly Detection (Phase 11+)
│   └── .gitkeep
│
├── tests/                              # Automated Test Suites (Phase 2+)
│   └── .gitkeep
│
└── scripts/                            # Operational & Inspection Utility Scripts (Phase 1+)
    └── .gitkeep
```

---

## 14. Development Rules
1. **Never Bypass the Semantic Layer**: All queries must map back to an authorized, mathematically defined metric.
2. **Never Allow Raw SQL Execution**: Only parameterized, read-only SQL generated via validated intent and vetted against the schema registry is permitted.
3. **Respect Role Scoping**: Data isolation between departments is an absolute rule enforced at the database query generation level.
4. **Preserve Repository Cleanliness**: No credentials, temporary dumps, or mock data files may ever be committed.
5. **Phase Gate Verification**: Every phase must conclude with automated checks, test passes, and explicit approval before moving forward.

---

## 15. Definition of Done (DoD) for Any Phase
A phase is considered **Done** only when:
1. All phase-specific objectives and deliverables are created.
2. No scope from future phases has been prematurely implemented.
3. All code passes linting, type-checking, and unit tests without warnings or errors.
4. Security and credential scans confirm zero secrets committed.
5. Documentation is synchronized with code changes.
6. Acceptance criteria in `docs/development-checklist.md` for that phase are 100% verified.
