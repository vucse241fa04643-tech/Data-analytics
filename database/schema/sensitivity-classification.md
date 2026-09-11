# Agent 63 – Data Sensitivity & Classification Policy

> **Mandate:** Protect student privacy, institutional security, and statutory confidentiality.
> **Enforcement:** Enforced at Schema Registry, Semantic Layer, and Backend Query Builders.

## Classification Tiers

### 1. `PUBLIC_ANALYTICS`
- **Description:** Institution-wide public facts, academic calendars, curriculum structures, and published regulations.
- **Objects:** `core.institution`, `core.academic_year`, `core.term`, `core.campus`, `curriculum.programme`, `curriculum.course`, `quality.kpi_definition`.
- **Agent 63 Action:** Permitted for all authenticated users without departmental filtering.

### 2. `INTERNAL_ANALYTICS`
- **Description:** Aggregated academic performance, cohort statistics, department benchmarks, and placement summaries.
- **Objects:** `attendance.v_current_attendance`, `assessment.v_course_performance`, `outcomes.v_attainment_trace`, `placement.readiness_summary`.
- **Agent 63 Action:** Permitted subject to RBAC role boundaries (Management sees college-wide, HOD sees department).

### 3. `ROLE_RESTRICTED`
- **Description:** Detailed operational and administrative data requiring explicit role clearance (e.g. Dean/Principal/IQAC).
- **Objects:** `finance.student_dues`, `hr.faculty_workload`, `exams.exam_session`, `governance.committee_meeting`.
- **Agent 63 Action:** Blocked for general queries; permitted only when requesting user possesses specific verified role.

### 4. `SENSITIVE`
- **Description:** Personal identifiable information (PII), disciplinary investigations, and staff appraisals.
- **Objects:** `studentlife.disciplinary_case`, `hr.faculty_appraisal`, `admissions.quota_allocation`.
- **Agent 63 Action:** Masked or withheld from LLM query generation.

### 5. `HIGHLY_SENSITIVE` / `DENY_GENERAL_ANALYTICS`
- **Description:** Psychological counselling records, medical notes, exam questions, and authentication credentials.
- **Objects:**
  - `confidential.*` (`counselling_case`, `counselling_note`, `medical_record`, `crisis_escalation`)
  - `assessment.question_paper`
  - `identity.auth_credential`, `identity.app_user` (password hashes, tokens)
- **Agent 63 Action:** **HARD DENY.** Excluded from Agent 63 Schema Registry allowlists. Queries targeting these objects are rejected before execution.

## Explicit Column Masking Rules

| Table | Column | Risk | Masking / Action |
| :--- | :--- | :--- | :--- |
| `people.person` | `aadhar_number` / `national_id` | Identity theft | EXCLUDED from query projection |
| `people.person` | `phone`, `email` | Privacy leak | Masked (`XXXXX-1234`) in student exports |
| `finance.fee_payment` | `transaction_reference` | Financial PII | Withheld from conversational answers |
| `confidential.*` | ALL COLUMNS | Statutory medical confidentiality | NEVER ACCESSED OR JOINED |