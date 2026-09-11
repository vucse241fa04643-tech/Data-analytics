# Agent 63 – Initial Analytics Scope Specification

> **Status:** Defined in Phase 1 for Semantic Layer (Phase 4) and Intent Parser (Phase 6).

## Priority Analytics Domains (Phase 1 Approved Scope)
The initial release of Agent 63 prioritizes nine core operational domains:

1. **`core`**: Institutional metadata, campuses, departments, terms, academic years, and classrooms.
2. **`people`**: Student demographics, faculty rosters, staff assignments, and profiles (`v_student_profile`).
3. **`curriculum`**: Programmes, regulations, batches, sections, courses, syllabi, and outcome definitions (CO/PO).
4. **`academics`**: Course offerings, student registrations, timetable delivery, lesson plans, and class progress.
5. **`attendance`**: Daily session attendance, student leaves, and aggregate attendance summaries (`v_current_attendance`).
6. **`assessment`**: Component assessments, question marks, internal marks, course grades, and term results (`v_course_performance`).
7. **`outcomes`**: Attainment rubrics, CO/PO calculation runs, and traceability traces (`v_attainment_trace`).
8. **`placement`**: Placement drives, company visits, job applications, offers, internships, and readiness scores.
9. **`quality`**: IQAC KPI definitions, periodic attainment values, and accreditation metrics (`v_kpi_latest`).

## Deferred / Restricted Domains (Future Phases)
- **`finance`**: Restricted fee transactions, ledger entries, and student dues.
- **`hr`**: Faculty appraisals, payroll metadata, and workload calculations.
- **`studentlife`**: Disciplinary cases and student grievances (high sensitivity).
- **`research`**, **`engagement`**, **`admissions`**, **`governance`**: Slated for Phase 12 executive dashboard integrations.
- **`identity`**: Restricted exclusively to user authorization, role verification, and audit logging. **Never directly queryable as an analytics source.**

## Strictly Denied Domain
- **`confidential`**: Complete exclusion. Medical records, counselling cases, and crisis escalation data will NEVER be queried or exposed.
