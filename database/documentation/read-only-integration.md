# Agent 63 – Read-Only Database Integration Architecture

> **Status:** Scaffolding Documented in Phase 1 (Connection deferred to runtime phases)

## 1. Connection Philosophy & Least Privilege
Agent 63 executes queries strictly via a dedicated PostgreSQL read-only database role. The database user must have zero write privileges:

```sql
-- Recommended PostgreSQL setup for Agent 63 read-only user
CREATE ROLE agent63_readonly WITH LOGIN PASSWORD 'CHANGE_IN_PRODUCTION';
GRANT CONNECT ON DATABASE academic_agent_platform TO agent63_readonly;
GRANT USAGE ON SCHEMA core, people, curriculum, academics, attendance, assessment, outcomes, placement, quality TO agent63_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA core, people, curriculum, academics, attendance, assessment, outcomes, placement, quality TO agent63_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA core, people, curriculum, academics, attendance, assessment, outcomes, placement, quality GRANT SELECT ON TABLES TO agent63_readonly;
REVOKE ALL ON SCHEMA confidential FROM agent63_readonly;
REVOKE ALL ON TABLE assessment.question_paper FROM agent63_readonly;
```

## 2. Resource Containment & Timeout Controls
- **Statement Timeout:** Default `5000ms` (5 seconds). Any query running longer than 5 seconds is terminated by PostgreSQL (`SET statement_timeout = '5000'`).
- **Connection Pool:** Managed via SQLAlchemy Core with a maximum of 10 connections (`pool_size=10, max_overflow=5`).
- **Read-Only Transaction State:** Connections explicitly set `default_transaction_read_only = on`.

## 3. Current Connection Status
- **Schema Definition Status:** Inspected and fully mapped (`schema_full.sql`).
- **Schema Authority Notice:**
  - `database/schema/01_foundation.sql` is **NOT** the complete college database schema (it contains only the foundation/core module).
  - `database/schema/schema_full.sql` is currently the **complete authoritative 21-domain schema** used for Agent 63 Phase 1 mapping.
  - All Phase 1 generated registries and mappings were generated from `schema_full.sql`.
  - Neither SQL file should be modified by Agent 63.
  - Future schema changes must be supplied/approved by the college and must not be invented by the development agent.
- **Live Database Connection Status:** **NOT CONFIGURED IN PHASE 1.**
- **Populated Production Data Availability:** **UNKNOWN / NOT CONNECTED.**
- Real student records have NOT been accessed; Phase 1 establishes the structural catalog only.
