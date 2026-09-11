# Agent 63 – College Data Quality & Analytical Quirks Analysis

> **Analysis:** Observations derived from physical schema inspection of `schema_full.sql`.
> **Purpose:** Guiding the Phase 4 Semantic Layer and Phase 8 Result Validator to avoid incorrect calculations.

## 1. Table Partitioning Behavior (`attendance` and `identity`)
- `attendance.attendance_record` is partitioned by range (`session_date`), e.g., `attendance_record_2026`, `attendance_record_2027`.
- `identity.audit_log` is partitioned by range (`occurred_at`), e.g., `audit_log_2026`, `audit_log_2027`.
- **Analytical Impact:** Query planners must include explicit date bounds in `WHERE` clauses to enable partition pruning and prevent expensive full-table scans across multi-year attendance tables.

## 2. Attendance Adjustment & Condonation (`attendance.attendance_summary`)
- The schema contains both raw `attendance_pct` and `adjusted_attendance_pct` (accounting for medical leaves and official duty leaves `student_leave`).
- **Rule for Semantic Layer:** Inquiries asking for 'Official Attendance' must query `adjusted_attendance_pct`, while inquiries asking for 'Physical Attendance' query `attendance_pct`.

## 3. Backlogs & Multi-Attempt Assessments (`assessment.backlog`)
- Students who fail an end-term examination reappear in subsequent terms (`assessment.backlog`).
- **Analytical Impact:** Calculating 'Pass Percentage' requires distinguishing between **First-Attempt Pass Rate** (cohort intake success) and **Final Graduating Pass Rate** (including backlog clearances).

## 4. Multiple Course Offerings per Term (`academics.course_offering`)
- A single course (e.g., *Data Structures*) may have 4 distinct offerings across sections A, B, C, and D in a single term.
- **Analytical Impact:** Aggregating marks or attendance across a course requires grouping by `course_id` across offerings, rather than assuming a 1-to-1 relationship between course and offering.

## 5. Nullable Analytical Dimensions
- `core.calendar_event.department_id` is nullable (NULL denotes an institution-wide event, whereas non-NULL denotes a department-specific holiday).
- `people.faculty.resigned_on` is nullable (NULL denotes actively serving faculty).
- **Analytical Impact:** Missing `IS NULL` filters on `resigned_on` would incorrectly inflate faculty-student ratio calculations.
