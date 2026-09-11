# Agent 63 – Semantic Layer & Institutional Metric Catalog

> **Phase 4 Deliverable**  
> **Status:** APPROVED & VALIDATED  
> **Target Database Engine:** PostgreSQL 14+ (236 registered schema objects)  
> **AI / LLM Integration Status:** **NOT IMPLEMENTED IN PHASE 4** (Introduced strictly in Phase 6 via backend orchestrator)

---

## 1. Architectural Purpose

The **Semantic Layer** is the authoritative, deterministic foundation for all institutional business analytics in Agent 63. It defines what university operational terms mean, documents exact mathematical formulas, specifies analytical grains, establishes controlled relational join paths, and enforces security classifications.

### Why Semantic Definitions Are Mandatory Before LLM Integration

A foundational vulnerability of conventional LLM-to-SQL systems is formula and join hallucination:
- When prompted for *"pass percentage"*, an unconstrained LLM may divide passed students by total registered students, or by appeared students, or compute an unweighted average of section averages.
- When prompted for *"attendance percentage"*, an LLM may ignore approved duty/medical leaves, misinterpret missing entries as 0%, or average student percentages across unequal section sizes.
- When linking entities, an unconstrained LLM may invent joins across unrelated foreign keys.

In Agent 63, **the LLM is strictly prohibited from inventing formulas, metric definitions, or relational joins**.

Instead, future natural language execution follows this immutable pipeline:

```text
Natural Language Query
         │
         ▼
Agent 63 Backend Orchestrator
         │
         ▼
Google Gemini (Phase 6: NL → Structured Intent ONLY)
         │  (Outputs typed IntentSchema referencing canonical metric_ids)
         ▼
Semantic Layer (Phase 4: Resolves metric formula, grain, joins, and filters)
         │
         ▼
RBAC Authorization Scope (Phase 5: Injects role/department boundaries)
         │
         ▼
Safe Parameterized SQL Generator (Phase 7: Compiles deterministic read-only AST)
         │
         ▼
College PostgreSQL Database (Phase 8: Executes read-only query with timeouts)
```

---

## 2. Directory Architecture

```text
semantic_layer/
├── README.md                      # Comprehensive architectural documentation
├── policies/
│   └── semantic_security.json     # Access tiers, confidential exclusions, and fairness constraints
├── dimensions/                    # Controlled analytical dimensions
│   ├── academic_year.json         # Academic calendar cycle dimension
│   ├── term.json                  # Semester / instructional period dimension
│   ├── department.json            # Academic department dimension
│   ├── programme.json             # Degree program dimension (B.Tech / M.Tech)
│   ├── batch.json                 # Student admission cohort dimension
│   ├── section.json               # Classroom section cohort dimension
│   ├── course.json                # Master course catalog version dimension
│   ├── course_offering.json       # Scheduled delivery instance dimension
│   ├── student.json               # Enrolled student dimension
│   └── faculty.json               # Instructional faculty dimension
├── joins/
│   └── join_paths.json            # 24 verified foreign-key join paths with cardinality
├── metrics/                       # Institutional metric definitions by domain
│   ├── attendance.json            # 6 attendance monitoring & shortage metrics
│   ├── assessment.json            # 6 academic performance, pass rate & CIA metrics
│   ├── outcomes.json              # 4 OBE CO/PO attainment & articulation metrics
│   ├── placement.json             # 6 campus recruitment, offer, CTC & readiness metrics
│   ├── academics.json             # 2 capacity & course delivery metrics
│   └── quality.json               # 2 IQAC institutional KPI & variance metrics
└── registry/
    └── semantic_registry.json     # Compiled, machine-readable master registry
```

---

## 3. Metric Specification Schema

Each metric definition in `semantic_layer/metrics/` conforms to the following standardized machine-readable schema:

| Field | Type | Description |
|---|---|---|
| `metric_id` | `string` | Globally unique identifier (e.g. `attendance.percentage`, `assessment.course_pass_percentage`). |
| `canonical_name` | `string` | Snake-case machine identifier used in intent parsing. |
| `display_name` | `string` | Human-readable title for UI rendering. |
| `description` | `string` | Precise institutional definition of the metric. |
| `domain` | `string` | Operational domain (`attendance`, `assessment`, `outcomes`, `placement`, `academics`, `quality`). |
| `category` | `string` | Functional classification (e.g. `academic_performance`, `obe_accreditation`). |
| `grain` | `string` | Exact dimensional level of detail (e.g. `student_course_offering`, `course_offering`, `batch`). |
| `formula` | `string` | Deterministic mathematical expression. |
| `aggregation` | `string` | Aggregation operator (`AVG`, `SUM`, `COUNT`, `COUNT_DISTINCT`, `RATIO`, `MAX`, `LATEST`). |
| `unit` | `string` | Unit of measure (`percentage`, `count`, `marks`, `inr_lakhs_per_annum`, `level_scale`). |
| `numerator` | `string` | Dividend expression or aggregate component. |
| `denominator` | `string` | Divisor expression (or `null` for counts/aggregates). |
| `source_objects` | `array` | Referenced database tables/views from `agent63_schema_registry.json`. |
| `source_columns` | `array` | Specific columns utilized from the source objects. |
| `allowed_dimensions` | `array` | List of valid dimension IDs (`dim.*`) along which this metric can be sliced. |
| `allowed_filters` | `array` | List of approved attributes for filter predicate injection. |
| `time_semantics` | `object` | Temporal basis (`time_dimension`, `time_column`, `period_grain`). |
| `null_handling` | `object` | Explicit rules for missing data and zero-division prevention. |
| `sensitivity` | `string` | Security tier (`PUBLIC_INSTITUTIONAL`, `INTERNAL_INSTITUTIONAL`, `SENSITIVE`, `RESTRICTED`). |
| `status` | `string` | Lifecycle state (`APPROVED`, `REVIEW_REQUIRED`, `DRAFT`, `DEPRECATED`). |
| `version` | `string` | Semantic definition version. |
| `provenance` | `string` | Citation of the authoritative schema view, table, or institutional policy. |
| `validation_notes` | `string` | Analytical details, distinctive quirks, or assumptions. |

---

## 4. Controlled Dimensions

The semantic layer registers **10 controlled dimensions**:

| Dimension ID | Dimension Name | Source Object | Key Column | Display Column | Sensitivity |
|---|---|---|---|---|---|
| `dim.academic_year` | Academic Year | `core.academic_year` | `academic_year_id` | `label` | `PUBLIC_INSTITUTIONAL` |
| `dim.term` | Academic Term | `core.term` | `term_id` | `label` | `PUBLIC_INSTITUTIONAL` |
| `dim.department` | Academic Department | `core.department` | `department_id` | `name` | `PUBLIC_INSTITUTIONAL` |
| `dim.programme` | Degree Programme | `curriculum.programme` | `programme_id` | `name` | `PUBLIC_INSTITUTIONAL` |
| `dim.batch` | Cohort Batch | `curriculum.batch` | `batch_id` | `label` | `PUBLIC_INSTITUTIONAL` |
| `dim.section` | Class Section | `curriculum.section` | `section_id` | `code` | `PUBLIC_INSTITUTIONAL` |
| `dim.course` | Curricular Course | `curriculum.course_version` | `course_version_id` | `course_code` | `PUBLIC_INSTITUTIONAL` |
| `dim.course_offering` | Course Offering | `academics.course_offering` | `course_offering_id` | `course_offering_id` | `INTERNAL_INSTITUTIONAL` |
| `dim.student` | Enrolled Student | `people.student` | `student_id` | `roll_no` | `SENSITIVE` |
| `dim.faculty` | Instructional Faculty | `people.faculty` | `faculty_id` | `employee_no` | `INTERNAL_INSTITUTIONAL` |

---

## 5. Controlled Relational Join Graph

The join path registry in `joins/join_paths.json` catalogs **24 verified joins**. Every join is derived directly from foreign keys in the authoritative `schema_full.sql`:

1. `core.academic_year` ──(1:N)──> `core.term`
2. `core.institution` ──(1:N)──> `core.department`
3. `core.department` ──(1:N)──> `curriculum.programme`
4. `curriculum.programme` ──(1:N)──> `curriculum.batch`
5. `curriculum.batch` ──(1:N)──> `curriculum.section`
6. `curriculum.course` ──(1:N)──> `curriculum.course_version`
7. `curriculum.course_version` ──(1:N)──> `academics.course_offering`
8. `core.term` ──(1:N)──> `academics.course_offering`
9. `curriculum.section` ──(1:N)──> `academics.course_offering`
10. `academics.course_offering` ──(1:N)──> `academics.student_registration`
11. `people.student` ──(1:N)──> `academics.student_registration`
12. `people.person` ──(1:1)──> `people.student`
13. `people.person` ──(1:1)──> `people.faculty`
14. `core.department` ──(1:N)──> `people.faculty`
15. `academics.course_offering` ──(1:N)──> `attendance.attendance_summary`
16. `people.student` ──(1:N)──> `attendance.attendance_summary`
17. `academics.course_offering` ──(1:N)──> `assessment.course_result`
18. `people.student` ──(1:N)──> `assessment.course_result`
19. `curriculum.course_outcome` ──(1:N)──> `curriculum.co_po_map`
20. `curriculum.programme_outcome` ──(1:N)──> `curriculum.co_po_map`
21. `people.student` ──(1:N)──> `placement.offer`
22. `placement.company` ──(1:N)──> `placement.offer`
23. `people.student` ──(1:N)──> `placement.readiness_summary`
24. `quality.kpi_definition` ──(1:N)──> `quality.kpi_value`

---

## 6. Metric Catalog Inventory (26 Metrics)

### 6.1 Attendance Domain (`attendance.json`)
- `attendance.percentage` (`APPROVED`): Average adjusted session attendance percentage via `attendance.v_current_attendance`.
- `attendance.raw_percentage` (`APPROVED`): Raw physical session attendance percentage without leave adjustments.
- `attendance.students_below_threshold` (`REVIEW_REQUIRED`): Count of students falling below attendance threshold (threshold requires institutional parameter injection).
- `attendance.course_aggregate` (`APPROVED`): Mean attendance percentage for a course offering.
- `attendance.section_aggregate` (`APPROVED`): Mean attendance percentage for a classroom section.
- `attendance.shortage_count` (`APPROVED`): Count of students classified in the institutional SHORTAGE condonation band.

### 6.2 Assessment Domain (`assessment.json`)
- `assessment.course_pass_percentage` (`APPROVED`): Proportion of examined candidates securing PASS status via `assessment.v_course_performance`.
- `assessment.average_total_marks` (`APPROVED`): Mean examination total marks scored in a course offering.
- `assessment.students_appeared` (`APPROVED`): Number of candidates appearing for course examination.
- `assessment.students_passed` (`APPROVED`): Number of candidates securing a passing grade.
- `assessment.failure_count` (`APPROVED`): Number of candidates failing examination requirements.
- `assessment.internal_marks_average` (`APPROVED`): Mean continuous internal assessment (CIA) marks scored.

### 6.3 Outcomes Domain (`outcomes.json`)
- `outcomes.co_attainment_level` (`APPROVED`): Evaluated attainment level for a Course Outcome via `outcomes.v_attainment_trace`.
- `outcomes.po_attainment_level` (`APPROVED`): Weighted attainment level for a Programme Outcome via `outcomes.v_attainment_trace`.
- `outcomes.co_attaining_percentage` (`APPROVED`): Percentage of evaluated students satisfying the target CO rubric.
- `outcomes.co_po_mapping_strength` (`APPROVED`): Matrix correlation level (1 to 3) linking Course and Programme Outcomes.

### 6.4 Placement Domain (`placement.json`)
- `placement.placed_students_count` (`APPROVED`): Unique graduating candidates with verified accepted offers.
- `placement.total_offers_count` (`APPROVED`): Total volume of verified job offers issued.
- `placement.average_ctc` (`APPROVED`): Mean annual Cost to Company (CTC) compensation package (INR LPA).
- `placement.highest_ctc` (`APPROVED`): Peak annual compensation package secured by a cohort candidate.
- `placement.placement_rate` (`REVIEW_REQUIRED`): Ratio of placed candidates to eligible graduating cohort (denominator cohort policy pending resolution).
- `placement.readiness_average_score` (`APPROVED`): Mean composite placement readiness assessment quotient (0-100).

### 6.5 Academics Domain (`academics.json`)
- `academics.active_student_strength` (`APPROVED`): Total active student head count.
- `academics.active_course_offerings` (`APPROVED`): Count of scheduled instructional offerings delivered in a term.

### 6.6 Quality Domain (`quality.json`)
- `quality.kpi_latest_value` (`APPROVED`): Authoritative IQAC KPI measured value via `quality.v_kpi_latest`.
- `quality.kpi_target_variance` (`APPROVED`): Percentage variance of latest KPI value relative to target benchmark.

---

## 7. Security & Ethical Governance

1. **Confidential Domain Total Exclusion**:
   - `confidential.*` objects (mental health records, counselling notes, crisis escalations, medical accommodations) are completely absent from all semantic definitions.
2. **Examination Security Protection**:
   - `assessment.question_paper`, `exams.question_paper_delivery`, and `exams.malpractice_incident` are strictly excluded from general analytics.
3. **Placement Fairness**:
   - Placement analytics metrics and dimensions strictly forbid filtering, grouping, or slicing by protected demographic traits (`gender`, `caste`, `religion`, `region`, `socioeconomic_category`).
4. **Lifecycle Segregation**:
   - Only metrics with `status = "APPROVED"` are returned by the backend `get_approved_metrics()` service for production query construction. `REVIEW_REQUIRED` metrics remain excluded until institutional sign-off.

---

## 8. Validation and Verification

Run the dedicated validator at any time:

```powershell
& .venv\Scripts\python.exe scripts/validate_semantic_layer.py
```

Validation output:
```text
============================================================
AGENT 63 SEMANTIC LAYER VALIDATION REPORT
============================================================
Total metrics:          26
  Approved:             24
  Review required:      2
  Deprecated:           0
Total dimensions:       10
Total joins:            24
Errors:                 0
Warnings:               0
============================================================
[SUCCESS] All semantic layer integrity, relational, and security rules passed.
```
