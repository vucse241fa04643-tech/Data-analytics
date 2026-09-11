# Agent 63 – College Database Relationship & Grain Architecture

> **Primary Focus:** Documenting authoritative joins, entity cardinalities, and analytical grains.
> **Source:** Inspected PostgreSQL 14+ institutional schema (`01_foundation.sql` / `schema_full.sql`)

## 1. Central Academic Grain: `academics.course_offering`
In the supplied college database, `academics.course_offering` is the **central operational nexus** for all academic delivery facts.
Every class delivery, attendance record, internal assessment, and faculty allocation connects through `course_offering`.

```
                       curriculum.course (What is taught)
                               │
                               ▼
core.term ──────────► academics.course_offering ◄────────── core.department
(When it is taught)            │                            (Who offers it)
                               ├──────────────────────────┐
                               ▼                          ▼
                 academics.student_registration   academics.class_session
                               │                          │
                               ▼                          ▼
                 assessment.course_result        attendance.attendance_record
```

## 2. Core Institutional Join Paths

### A. Student Enrollment & Academic Progression Path
```sql
-- Trace student from institutional cohort to class registration
people.student (student_id)
  INNER JOIN people.person ON student.person_id = person.person_id
  INNER JOIN curriculum.programme ON student.programme_id = programme.programme_id
  INNER JOIN curriculum.batch ON student.batch_id = batch.batch_id
  LEFT JOIN curriculum.section ON student.current_section_id = section.section_id
  INNER JOIN academics.student_registration ON student.student_id = student_registration.student_id
  INNER JOIN academics.course_offering ON student_registration.course_offering_id = course_offering.course_offering_id
  INNER JOIN curriculum.course ON course_offering.course_id = course.course_id;
```

### B. Student Attendance Verification Path
```sql
-- Attendance aggregates connect student to offering and session details
attendance.attendance_summary (summary_id)
  INNER JOIN people.student ON attendance_summary.student_id = student.student_id
  INNER JOIN academics.course_offering ON attendance_summary.course_offering_id = course_offering.course_offering_id
  INNER JOIN core.term ON course_offering.term_id = term.term_id
  INNER JOIN core.department ON course_offering.department_id = department.department_id;
```

### C. Examination, Internal Assessment & Results Path
```sql
-- Connect assessment marks to individual students and course offerings
assessment.student_assessment_mark (mark_id)
  INNER JOIN assessment.assessment ON student_assessment_mark.assessment_id = assessment.assessment_id
  INNER JOIN academics.course_offering ON assessment.course_offering_id = course_offering.course_offering_id
  INNER JOIN people.student ON student_assessment_mark.student_id = student.student_id;
```

### D. Outcome-Based Education (OBE) Attainment Path
```sql
-- Trace student outcome attainment back to course competencies
outcomes.co_attainment (co_attainment_id)
  INNER JOIN curriculum.course_outcome ON co_attainment.course_outcome_id = course_outcome.course_outcome_id
  INNER JOIN curriculum.co_po_map ON course_outcome.course_outcome_id = co_po_map.course_outcome_id
  INNER JOIN curriculum.programme_outcome ON co_po_map.programme_outcome_id = programme_outcome.programme_outcome_id;
```

## 3. Analytical Grains Catalog

| Object | Natural Grain | Primary Identifier | Temporal Dimensions | Key Measures |
| :--- | :--- | :--- | :--- | :--- |
| `people.student` | One record per admitted student | `student_id` | `admission_year`, `expected_graduation_year` | Student count |
| `academics.course_offering` | One offering of a course in a specific term | `course_offering_id` | `core.term.academic_year_id` | Registered capacity, session count |
| `academics.student_registration` | One student enrolled in one course offering | `registration_id` | `registered_on` | Enrollment count |
| `attendance.attendance_record` | One student attendance fact per class session | `attendance_record_id` | `session_date` | Present / Absent / Late / On-Duty |
| `attendance.attendance_summary` | Cumulative attendance for a student in an offering | `summary_id` | `term_id` | `attended_sessions`, `total_sessions`, `attendance_pct` |
| `assessment.assessment` | One scheduled assessment component | `assessment_id` | `conducted_on` | `max_marks`, `weightage` |
| `assessment.student_assessment_mark` | Marks earned by one student in one component | `mark_id` | `marked_at` | `marks_obtained`, `is_absent` |
| `assessment.course_result` | Final grade for a student in an offering | `course_result_id` | `published_on` | `total_marks`, `grade_point`, `is_passed` |
| `outcomes.co_attainment` | Attainment score for a CO in an offering | `co_attainment_id` | `calculated_at` | `attainment_level_achieved`, `target_pct` |
| `placement.offer` | One job offer received by a student | `offer_id` | `offered_on` | `ctc_lpa`, `stipend_monthly` |
| `quality.kpi_value` | Periodic measurement of an institutional KPI | `kpi_value_id` | `academic_year_id`, `period_start` | `measured_value`, `target_value` |