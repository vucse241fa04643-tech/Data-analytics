# Canonical Schema Authority & Multi-File Notice

> **Important Notice for Institutional Governance & Future Development Phases**  
> **Date:** Phase 1 Final Consistency Audit

---

## 1. Schema Files Status & Relationship

The `database/schema/` directory contains two SQL files supplied by the college administration:

1. **`database/schema/01_foundation.sql` (192 lines, ~8.9 KB):**
   - **Scope:** Foundation & Core Module ONLY.
   - **Content:** Declares PostgreSQL extensions, initializes all 21 schema namespaces, defines shared audit triggers (`core.set_row_audit()`, `core.add_audit_columns()`), and creates the 10 reference tables of the `core` schema (`institution`, `campus`, `department`, `academic_year`, `term`, `calendar_event`, `building`, `room`, `code_list`, `code_value`).
   - **Crucial Distinction:** This file is **NOT** the complete college database schema. It does not contain academic records, student enrollments, course offerings, attendance, assessments, or placements.

2. **`database/schema/schema_full.sql` (3,987 lines, ~188.5 KB):**
   - **Scope:** Complete Authoritative Institutional Schema across all 21 domains.
   - **Content:** Contains the exact foundation prefix of `01_foundation.sql` plus all remaining 215 institutional tables, 11 analytical views, 9 security/scoping functions, and 19 Row Level Security (RLS) policies.
   - **Canonical Role:** **`schema_full.sql` is currently the complete authoritative source of truth for Agent 63.**

---

## 2. Derivation & Registry Traceability

- **All Phase 1 generated registries, inventories, dictionaries, and mappings were generated strictly from `database/schema/schema_full.sql`:**
  - Machine-readable schema inventory: [`database/schema/college_schema_inventory.json`](file:///c:/Users/manne/Desktop/data%20analytics%20agent/Data-analytics/database/schema/college_schema_inventory.json) (225 tables, 11 views, 21 schemas).
  - Agent 63 Schema Registry allowlist: [`database/mappings/agent63_schema_registry.json`](file:///c:/Users/manne/Desktop/data%20analytics%20agent/Data-analytics/database/mappings/agent63_schema_registry.json) (236 registered objects).
  - Academic Data Dictionary: [`database/schema/college_data_dictionary.md`](file:///c:/Users/manne/Desktop/data%20analytics%20agent/Data-analytics/database/schema/college_data_dictionary.md).
  - Entity-Relationship Maps & Grains: [`database/schema/college_relationships.md`](file:///c:/Users/manne/Desktop/data%20analytics%20agent/Data-analytics/database/schema/college_relationships.md).
  - Data Sensitivity Tiers: [`database/schema/sensitivity-classification.md`](file:///c:/Users/manne/Desktop/data%20analytics%20agent/Data-analytics/database/schema/sensitivity-classification.md).

---

## 3. Strict Non-Negotiable Governance Rules

1. **Zero Database Mutation by Agent 63:**
   - Neither `01_foundation.sql` nor `schema_full.sql` may be edited, reformatted, modified, or deleted by Agent 63.
   - The production database will be accessed strictly via read-only connections (`agent63_readonly`).
2. **External College Authority:**
   - Future schema changes, table additions, column modifications, or constraint adjustments must be supplied and approved officially by the college administration.
   - The development agent and LLM pipeline **must NEVER invent new tables, synthetic schemas, or mock institutional columns**.
