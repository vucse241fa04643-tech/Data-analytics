# Agent 63 – Database Security & RLS Integration Analysis

> **Inspection:** Analysis of Row Level Security (RLS) and Audit Mechanisms in `schema_full.sql`.

## 1. Discovered Row Level Security (RLS) Tables
The college schema explicitly enables RLS on 7 sensitive tables:

- `agentops.risk_flag`
- `assessment.internal_mark`
- `assessment.question_paper`
- `attendance.attendance_summary`
- `confidential.counselling_case`
- `confidential.counselling_note`
- `studentlife.disciplinary_case`

## 2. Discovered Security Policies
| Table | Policy Name | Command | Target Roles | Using Expression |
| :--- | :--- | :--- | :--- | :--- |
| `attendance.attendance_summary` | `att_summary_self` | `SELECT` | `PUBLIC` | `student_id = identity.current_student_id()...` |
| `attendance.attendance_summary` | `att_summary_teaching_faculty` | `SELECT` | `PUBLIC` | `course_offering_id IS NOT NULL     AND academics.teaches_off...` |
| `attendance.attendance_summary` | `att_summary_mentor` | `SELECT` | `PUBLIC` | `studentlife.is_mentor_of(student_id)...` |
| `attendance.attendance_summary` | `att_summary_dept_leadership` | `SELECT` | `PUBLIC` | `(identity.has_role('HOD') OR identity.has_role('DEAN') OR id...` |
| `attendance.attendance_summary` | `att_summary_institution` | `ALL` | `PUBLIC` | `identity.has_role('PRINCIPAL') OR identity.has_role('SYSTEM'...` |
| `assessment.internal_mark` | `internal_mark_self` | `SELECT` | `PUBLIC` | `student_id = identity.current_student_id()     AND is_provis...` |
| `assessment.internal_mark` | `internal_mark_faculty` | `ALL` | `PUBLIC` | `academics.teaches_offering(course_offering_id)...` |
| `assessment.internal_mark` | `internal_mark_leadership` | `SELECT` | `PUBLIC` | `(identity.has_role('HOD') OR identity.has_role('DEAN') OR id...` |
| `assessment.question_paper` | `qp_setter_moderator` | `ALL` | `PUBLIC` | `(setter_faculty_id = identity.current_faculty_id()      OR m...` |
| `assessment.question_paper` | `qp_coe` | `ALL` | `PUBLIC` | `identity.has_role('COE')...` |
| `confidential.counselling_case` | `counselling_counsellor` | `ALL` | `PUBLIC` | `identity.has_role('COUNSELLOR')     AND (counsellor_user_id ...` |
| `confidential.counselling_case` | `counselling_self` | `SELECT` | `PUBLIC` | `student_id = identity.current_student_id()...` |
| `confidential.counselling_note` | `counselling_note_counsellor` | `ALL` | `PUBLIC` | `identity.has_role('COUNSELLOR')     AND counsellor_user_id =...` |
| `studentlife.disciplinary_case` | `disc_authority` | `ALL` | `PUBLIC` | `(identity.has_role('DISCIPLINE_COMMITTEE') OR identity.has_r...` |
| `studentlife.disciplinary_case` | `disc_self` | `SELECT` | `PUBLIC` | `student_id = identity.current_student_id() AND retention_unt...` |
| `agentops.risk_flag` | `flag_responder` | `ALL` | `PUBLIC` | `responder_user_id = identity.current_user_id()...` |
| `agentops.risk_flag` | `flag_mentor` | `SELECT` | `PUBLIC` | `student_id IS NOT NULL AND studentlife.is_mentor_of(student_...` |
| `agentops.risk_flag` | `flag_academic_leadership` | `SELECT` | `PUBLIC` | `(identity.has_role('HOD') OR identity.has_role('DEAN'))     ...` |
| `agentops.risk_flag` | `flag_counsellor` | `SELECT` | `PUBLIC` | `identity.has_role('COUNSELLOR') AND flag_type = 'WELLBEING_C...` |

## 3. Built-in Authorization Helper Functions
The college database defines modular PostgreSQL functions for context-aware security:

- **`core.set_row_audit()`** $\rightarrow$ `trigger`
- **`core.add_audit_columns(p_table regclass)`** $\rightarrow$ `void`
- **`identity.current_user_id()`** $\rightarrow$ `uuid`
- **`identity.current_student_id()`** $\rightarrow$ `uuid`
- **`identity.current_faculty_id()`** $\rightarrow$ `uuid`
- **`identity.has_role(p_role text)`** $\rightarrow$ `boolean`
- **`identity.dept_scope() RETURNS uuid[] AS $$   SELECT CASE     WHEN coalesce(current_setting('app.dept_scope', true), '') = '' THEN ARRAY[]::uuid[]     ELSE string_to_array(current_setting('app.dept_scope', true), ',')::uuid[]   END $$ LANGUAGE sql STABLE;  -- Does the current faculty user teach this offering? CREATE OR REPLACE FUNCTION academics.teaches_offering(p_offering uuid)`** $\rightarrow$ `boolean`
- **`studentlife.is_mentor_of(p_student uuid)`** $\rightarrow$ `boolean`
- **`people.student_in_scope(p_student uuid)`** $\rightarrow$ `boolean`
- **`identity.block_audit_mutation()`** $\rightarrow$ `trigger`

## 4. Integration Strategy for Agent 63
Agent 63's future authorization layer (Phase 5) will complement rather than circumvent database security:
1. **Session Variables:** Before executing queries, the query executor sets PostgreSQL session variables corresponding to user claims (e.g., `SET LOCAL app.user_id = '...'`, `SET LOCAL app.department_id = '...'`).
2. **Dual Enforcement:** Scopes are injected in Python SQL generation AND verified by database RLS policies for defense-in-depth.
3. **Zero Mutation Triggers:** Audit triggers (`core.set_row_audit()`) will never be fired because Agent 63 operates exclusively with `SELECT` queries.