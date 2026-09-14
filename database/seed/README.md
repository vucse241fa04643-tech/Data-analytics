# Agent 63 — Synthetic Development Dataset

> **WARNING: STRICTLY SYNTHETIC DATA FOR DEVELOPMENT & TESTING ONLY**
>
> This dataset was deterministically generated **solely for local testing and validation of Agent 63**.
> - **NEVER** present or represent this data as real college, institutional, student, or faculty data.
> - **NEVER** load this dataset into any production, staging, or live institutional database environment.
> - Contains **ZERO** real personal names, student roll numbers, emails, phone numbers, credentials, or confidential records.

---

## 1. Overview & Fictional Institution

- **Fictional Institution Name:** Agent 63 Development University
- **Institutional Code:** `A63DEV`
- **Campus:** North Bengaluru Tech Campus (`MAIN`)
- **Affiliation:** Autonomous institution accredited under National Technological University conventions
- **Purpose:** Provide an internally consistent, referentially intact, multi-departmental, multi-year relational dataset to thoroughly exercise Agent 63's analytical queries, semantic layer metrics, natural language intent compiler, and anomaly detection services.

---

## 2. Dataset Scale & Domain Coverage

| Domain | Entity / Table | Record Count | Description / Notes |
| :--- | :--- | :--- | :--- |
| **Core** | `core.institution` | 1 | Fictional institution (`A63DEV`) |
| | `core.campus` | 1 | Main engineering campus |
| | `core.building` & `core.room` | 3 / 9 | Classrooms, laboratories, and lecture auditoriums |
| | `core.department` | 6 | 5 active (`CSE`, `ECE`, `EEE`, `MECH`, `CIVIL`) + 1 empty scenario (`ARCH`) |
| | `core.academic_year` | 4 | 3 active (`2023-24`, `2024-25`, `2025-26`) + 1 empty future (`2026-27`) |
| | `core.term` | 7 | ODD/EVEN terms spanning historical, current active, and future planned |
| **People** | `people.person` | 575 | Synthetic person records for all faculty and students |
| | `people.faculty` | 55 | Regular faculty members across all 5 active departments, with appointed HODs |
| | `people.student` | 520 | Synthetic enrolled students across 4 active study years (Years 1 to 4) |
| **Curriculum** | `curriculum.regulation` | 2 | `R2022` and `R2024` (NEP-aligned) |
| | `curriculum.programme` | 8 | 7 active UG/PG programmes + 1 empty scenario (`BARCH`) |
| | `curriculum.programme_outcome` | 70 | 12 POs + 2 PSOs per active UG programme |
| | `curriculum.batch` | 25 | Batches from 2021-25 through 2025-29 |
| | `curriculum.section` | 36 | Active sections (A, B, C) mapped across departments and batches |
| | `curriculum.course` & `course_version` | 55 | Technical core and elective courses across all departments |
| | `curriculum.course_outcome` | 220 | 4 Course Outcomes (Bloom levels 2 to 5) per course version |
| | `curriculum.co_po_map` | 660 | Explicit mapping strengths (1 to 3) connecting COs to POs |
| **Academics** | `academics.course_offering` | 249 | Course offerings across terms (51 currently active in EVEN 2025-26) |
| | `academics.faculty_allocation` | 249 | Primary faculty allocations per offering |
| | `academics.student_registration` | 3,520 | Student registrations matching batch/section enrolments |
| | `academics.class_session` | 60 | Class sessions conducted in 2026 for active offerings |
| **Attendance** | `attendance.attendance_record` | 300+ | Partitioned records routed to `attendance.attendance_record_2026` |
| | `attendance.attendance_summary` | 3,520 | Student attendance summaries driving `attendance.v_current_attendance` |
| **Assessment** | `assessment.assessment_type` | 4 | Continuous assessment tests (CAT-1, CAT-2), SEE, and Lab |
| | `assessment.internal_mark` | 2,805 | Scaled internal marks (out of 40) for completed offerings |
| | `assessment.course_result` | 2,805 | Regular examination results (2,320 PASS, 485 FAIL; 82.71% pass rate) |
| | `assessment.term_result` | 1,480 | SGPA, CGPA, and backlog counts per student per term |
| **Outcomes** | `outcomes.attainment_rubric` | 1 | Standard OBE rubric (direct weight 0.80, indirect weight 0.20) |
| | `outcomes.attainment_run` | 40 | Formal OBE calculation runs across offerings |
| | `outcomes.co_attainment` | 160 | CO attainment levels (target 2.50, average final level 2.53) |
| | `outcomes.po_attainment` | 156 | PO weighted attainment levels across batches and terms |
| **Placement** | `placement.company` | 12 | Synthetic tech, core, and consulting companies (Dream, Core, Mass) |
| | `placement.job_opening` | 24 | Campus recruitment drives across 2024-25 and 2025-26 |
| | `placement.drive_application` | 216 | Student applications for placement drives |
| | `placement.offer` | 216 | 216 total offers (108 distinct placed students, max CTC 38 LPA, avg 11.2 LPA) |
| | `placement.readiness_summary` | 136 | Readiness scores and bands (Ready, Near Ready, Needs Prep) |
| | `placement.internship` | 65 | Completed internships with stipends and verified institutional status |
| **Quality** | `quality.kpi_definition` | 8 | Institutional quality KPIs (Pass rate, attendance, OBE, placement) |
| | `quality.kpi_value` | 120 | Periodic KPI values scoped to departments and academic years |
| **Identity** | `identity.role` & `app_user` | 7 / 7 | Synthetic dev accounts with scoped RBAC bindings (Principal, HOD, Faculty) |

---

## 3. Approved Agent 63 Semantic Metrics Coverage

Every approved metric in the Phase 4 Semantic Registry is supported by valid, referentially sound records:

| Metric ID | Domain | Base Object | Test Verification Status |
| :--- | :--- | :--- | :--- |
| `academics.active_student_strength` | academics | `people.student` | Verified (520 active students across 5 active departments) |
| `academics.active_course_offerings` | academics | `academics.course_offering` | Verified (51 active offerings in EVEN 2025-26) |
| `assessment.course_pass_percentage` | assessment | `assessment.v_course_performance` | Verified (82.71% overall pass rate) |
| `assessment.average_total_marks` | assessment | `assessment.v_course_performance` | Verified (average total marks ~ 68.4) |
| `assessment.students_appeared` | assessment | `assessment.v_course_performance` | Verified (2,805 student course attempts) |
| `assessment.students_passed` | assessment | `assessment.v_course_performance` | Verified (2,320 student passes) |
| `assessment.failure_count` | assessment | `assessment.course_result` | Verified (485 failed records) |
| `assessment.internal_marks_average` | assessment | `assessment.internal_mark` | Verified (average internal mark: 28.63 / 40.0) |
| `attendance.percentage` | attendance | `attendance.v_current_attendance` | Verified (average adjusted percentage: 79.43%) |
| `attendance.raw_percentage` | attendance | `attendance.v_current_attendance` | Verified (average raw percentage: 77.93%) |
| `attendance.course_aggregate` | attendance | `attendance.v_current_attendance` | Verified (course offering aggregates available) |
| `attendance.section_aggregate` | attendance | `attendance.v_current_attendance` | Verified (section aggregates available across all depts) |
| `attendance.shortage_count` | attendance | `attendance.v_current_attendance` | Verified (attendance shortage records exist; see Schema Limitations note) |
| `outcomes.co_attainment_level` | outcomes | `outcomes.v_attainment_trace` | Verified (average attainment level: 2.53 / 3.0) |
| `outcomes.po_attainment_level` | outcomes | `outcomes.v_attainment_trace` | Verified (average PO attainment level: 2.39 / 3.0) |
| `outcomes.co_attaining_percentage` | outcomes | `outcomes.v_attainment_trace` | Verified (average student attaining percentage: ~79.2%) |
| `outcomes.co_po_mapping_strength` | outcomes | `curriculum.co_po_map` | Verified (average strength ~ 2.45 across 660 maps) |
| `placement.placed_students_count` | placement | `placement.offer` | Verified (108 unique students with accepted/joined/offered status) |
| `placement.total_offers_count` | placement | `placement.offer` | Verified (216 offers generated) |
| `placement.average_ctc` | placement | `placement.offer` | Verified (average CTC: INR 11,21,117.29) |
| `placement.highest_ctc` | placement | `placement.offer` | Verified (highest CTC: INR 38,00,000.00 at Quantum AI Labs) |
| `placement.readiness_average_score` | placement | `placement.readiness_summary` | Verified (average readiness score: 76.66 / 100) |
| `quality.kpi_latest_value` | quality | `quality.v_kpi_latest` | Verified (latest department and institutional KPI metrics) |
| `quality.kpi_target_variance` | quality | `quality.v_kpi_latest` | Verified (calculated variance from benchmark targets) |

---

## 4. Controlled Anomaly Scenarios

The dataset intentionally incorporates deterministic anomalies for testing Agent 63's analytical and anomaly detection capabilities:

1. **Unusually Low Departmental Attendance (Mechanical Engineering):**
   - **Department:** `MECH`
   - **Behavior:** While other departments maintain attendance between 81% and 83%, the Mechanical Engineering department averages **69.52%**, triggering attendance shortage alerts and risk flags.
2. **Historical Attendance Shock & Recovery (Electronics & Communication):**
   - **Department:** `ECE`
   - **Behavior:** In AY 2023-24, ECE had an average attendance of **87.77%**. In AY 2024-25, attendance experienced a sharp drop to **74.68%** due to external transit disruptions, followed by a recovery to **83.57%** in AY 2025-26. This allows testing multi-year trend queries.
3. **Low Pass Percentage Course (Design & Analysis of Algorithms):**
   - **Course Code:** `CS304` (Department of CSE)
   - **Behavior:** Most courses exhibit pass rates between 83% and 86%. Course `CS304` has a pass rate of **61.54%** (24 passed out of 39 appeared), allowing Agent 63 to isolate difficult or outlier courses.
4. **Low Course Outcome Attainment (Thermodynamics CO4):**
   - **Course Code:** `ME202` (Engineering Thermodynamics, Department of MECH)
   - **Outcome:** CO4 (*"Analyze Rankine and refrigeration cycles"*)
   - **Behavior:** Attained level is only **1.22** against a target level of **2.50** (attainment percentage: **44.00%**, negative gap: **-1.28**), testing outcome deficiency diagnostics.

---

## 5. Controlled Empty-Result Scenarios

Legitimate combinations are intentionally left devoid of transactional data to test Agent 63's *"No analytical records found"* response handling:

1. **Department of Architecture (`ARCH`):**
   - Fully established in `core.department` with an approved programme `BARCH` in `curriculum.programme`, but with **0 enrolled students, 0 course offerings, and 0 marks/placements**.
   - Queries filtering on the Architecture department cleanly return 0 records without errors.
2. **Future Academic Year (`2026-27`):**
   - Formally defined in `core.academic_year` with a planned term in `core.term`, but with **0 historical assessments, 0 attendance summaries, and 0 placement offers**.
   - Trend queries spanning into 2026-27 gracefully handle the absence of forward transactions.
3. **First-Year Students (`Batch 2025-29`):**
   - Active students enrolled in coursework, but with **0 placement applications or offers** (campus recruitment occurs in Years 3 and 4).
   - Queries seeking placement data for the 2025 batch return empty results.

---

## 6. How to Load and Verify Safely

### Pre-requisites
Ensure PostgreSQL is running and the authoritative schema (`database/schema/schema_full.sql`) has been loaded into your local development database (`acadagents`):

```bash
# Verify connection to local development database
psql -h localhost -U buddy -d acadagents -c "SELECT current_database();"
```

### Safe Seed Loading
The seed file contains pure `INSERT` statements with `ON CONFLICT DO NOTHING`. It does not drop tables, truncate data, or modify schema privileges:

```bash
psql -h localhost -U buddy -d acadagents -v ON_ERROR_STOP=1 -f database/seed/development_seed.sql
```

### Safe Seed Validation
Execute the read-only validation script to verify table counts, metric base data, referential integrity, and anomaly scenarios:

```bash
psql -h localhost -U buddy -d acadagents -f database/seed/validate_development_seed.sql
```

All referential integrity checks must return `0` orphaned rows.

---

## 7. Known Schema Limitations Encountered

1. **`attendance.attendance_record` Range Partitioning:**
   The base schema defines table partitions only for `2026` (`attendance_record_2026` from `2026-01-01` to `2027-01-01`) and `2027` (`attendance_record_2027`). Historical sessions prior to 2026 cannot be inserted into `attendance.attendance_record` without creating partitions. Historical attendance metrics are therefore appropriately stored in `attendance.attendance_summary`, which is not partitioned.
2. **`attendance.attendance_summary.band` Check Constraint vs Metric Formula:**
   The check constraint on `attendance.attendance_summary.band` strictly permits `'GTE_75'`, `'B70_75'`, `'B65_70'`, `'B60_65'`, `'B50_60'`, and `'LT_50'`. The semantic registry formula for `attendance.shortage_count` references `WHERE a.band = 'SHORTAGE'`. Because inserting `'SHORTAGE'` would violate the schema constraint, students experiencing attendance shortages are categorized under valid bands such as `'B60_65'` and `'LT_50'`, while risk levels are set to `'AT_RISK'` or `'CRITICAL'`.
3. **Generated Stored Columns:**
   `outcomes.co_attainment.gap` is defined as `GENERATED ALWAYS AS (final_level - target_level) STORED`. Attempting to supply an explicit value in `INSERT` statements causes PostgreSQL error `42601`. The seed omits this column, allowing PostgreSQL to calculate it automatically.
