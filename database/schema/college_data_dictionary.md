# Agent 63 – College Database Data Dictionary

> [!IMPORTANT]
> **Schema Authority Notice:**
> - `database/schema/01_foundation.sql` is **NOT** the complete college database schema; it contains only the foundation/core module (10 tables of `core`).
> - `database/schema/schema_full.sql` is currently the **complete authoritative 21-domain schema** (225 tables, 11 views, 19 RLS policies) used for Agent 63 Phase 1 mapping.
> - All Phase 1 generated registries, data dictionaries, and mappings were generated from `schema_full.sql`.
> - Neither SQL file should be modified by Agent 63.
> - Future schema changes must be supplied/approved by the college and must not be invented by the development agent.

> **Scale:** 21 Schemas, 225 Tables, 11 Views, 7 RLS Tables, 19 Security Policies

## Overview of Institutional Schemas

| Schema | Description | Classification | Initial Agent 63 Status |
| :--- | :--- | :--- | :--- |
| `core` | Institutional profile, campuses, departments, academic calendar, terms, and physical room assets. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `people` | Supertype person registry, student profiles, faculty records, and staff master data. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `identity` | Application users, roles, permissions, audit trails, data requests, and session tokens. | `ROLE_RESTRICTED` | RESTRICTED |
| `curriculum` | Academic programmes, regulations, batches, sections, courses, units, topics, and outcomes (CO/PO). | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `academics` | Course offerings, student registrations, faculty allocations, timetables, lesson plans, class sessions, and syllabus coverage. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `attendance` | Class session attendance records, leave applications, daily tracking, and aggregated attendance summaries. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `assessment` | Assessment definitions, student question marks, component marks, internal marks, course results, term results, backlogs, and question papers. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `exams` | Examination sessions, candidate seat allocations, invigilation duties, paper delivery tracking, and malpractice incidents. | `ROLE_RESTRICTED` | RESTRICTED |
| `outcomes` | Outcome-based education (OBE) attainment rubrics, calculation runs, CO attainment, and PO attainment traces. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `research` | Faculty and student publications, research grants, patents, citations, thesis tracking, and project supervision. | `ROLE_RESTRICTED` | RESTRICTED |
| `engagement` | Institutional events, industry collaborations, MOUs, community outreach, and guest lectures. | `ROLE_RESTRICTED` | RESTRICTED |
| `admissions` | Application intake, entrance rank verification, quota allocations, document verifications, and enrollment conversions. | `ROLE_RESTRICTED` | RESTRICTED |
| `finance` | Student fee structures, fee payments, dues tracking, scholarships, fee waivers, and institutional ledger heads. | `SENSITIVE` | RESTRICTED |
| `studentlife` | Mentoring relationships, student grievances, clubs, sports achievements, and disciplinary cases. | `SENSITIVE` | RESTRICTED |
| `placement` | Corporate partners, job openings, placement drive registrations, student offers, internship tracking, and alumni career paths. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `hr` | Faculty workload allocations, performance appraisals, leave balances, professional development records, and payroll profiles. | `SENSITIVE` | RESTRICTED |
| `governance` | Statutory bodies (BoS, Academic Council, Governing Body), policies, meeting minutes, and compliance circulars. | `ROLE_RESTRICTED` | RESTRICTED |
| `quality` | Internal Quality Assurance Cell (IQAC) KPI definitions, periodic measurements, accreditation metrics (NAAC/NBA/NIRF), and feedback surveys. | `INTERNAL_ANALYTICS` | ALLOWED (Scoped) |
| `knowledge` | Institutional documentation, policy PDF chunking, embedding vectors, and RAG knowledge extraction. | `ROLE_RESTRICTED` | RESTRICTED |
| `agentops` | Agent registry, tool definitions, execution runs, human reviews, safety flags, and fairness monitoring. | `ROLE_RESTRICTED` | RESTRICTED |
| `confidential` | Medical accommodations, psychological counselling notes, and crisis escalation data. Strictly isolated. | `DENY_GENERAL_ANALYTICS` | DENIED |

---

## Core Institutional Analytics Data Dictionary


### Schema: `core`

*Institutional profile, campuses, departments, academic calendar, terms, and physical room assets.*

#### Table: `core.institution`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `institution_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `affiliating_body` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `aishe_code` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `address` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.campus`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `campus_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `address` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.department`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `department_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `short_name` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `hod_faculty_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `established_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.academic_year`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `academic_year_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `label` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `start_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `end_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_current` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.term`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `term_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `academic_year_id` | `uuid` | NO | - | core.academic_year(id) | `INTERNAL` | `ALLOW` |
| `term_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `label` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `parity` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `start_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `end_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `instruction_end` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.calendar_event`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `calendar_event_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `academic_year_id` | `uuid` | NO | - | core.academic_year(id) | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | YES | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `event_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `end_date` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `event_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `blocks_instruction` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.building`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `building_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `campus_id` | `uuid` | NO | - | core.campus(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.room`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `room_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `building_id` | `uuid` | NO | - | core.building(id) | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | YES | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `room_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `seating_capacity` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `exam_capacity` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `equipment` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.code_list`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `code_list_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `description` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `core.code_value`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `code_value_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `code_list_id` | `uuid` | NO | - | core.code_list(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `label` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `sort_order` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `attributes` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |



### Schema: `people`

*Person supertype, student profiles, faculty records, and staff master data.*

#### Table: `people.person`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `person_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `full_name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `given_name` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `family_name` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `date_of_birth` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `gender` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `primary_email` | `text` | YES | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `primary_phone` | `text` | YES | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `photo_ref` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `nationality` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `address` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `social_category` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_differently_abled` | `boolean` | YES | - | - | `INTERNAL` | `ALLOW` |
| `mother_tongue` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `merged_into` | `uuid` | YES | - | people.person(id) | `INTERNAL` | `ALLOW` |


#### Table: `people.person_identifier`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `person_identifier_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `system_code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `identifier` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_primary` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `people.student`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `admission_no` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `roll_no` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `register_no` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `batch_id` | `uuid` | NO | - | - | `INTERNAL` | `ALLOW` |
| `admission_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `admission_category` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `entry_qualification` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `current_section_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `current_year_of_study` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status_changed_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `graduation_date` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `people.guardian`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guardian_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `relation` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `phone` | `text` | YES | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `email` | `text` | YES | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `occupation` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `annual_income` | `numeric(12,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_primary_contact` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `contact_consent` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `people.faculty`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `faculty_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `employee_no` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | NO | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `designation` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `cadre` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `employment_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `highest_qualification` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_phd_holder` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `phd_awarded_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `date_of_joining` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `date_of_leaving` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_research_supervisor` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `people.faculty_expertise`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `faculty_expertise_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `faculty_id` | `uuid` | NO | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `area` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `proficiency` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evidence_source` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `people.staff`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `staff_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `employee_no` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | YES | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `designation` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `category` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `date_of_joining` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `people.student_lab_batch`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `lab_batch_id` | `uuid` | NO | - | curriculum.lab_batch(id) | `INTERNAL` | `ALLOW` |



### Schema: `curriculum`

*Programmes, regulations, batches, sections, courses, units, topics, and outcomes (CO/PO).*

#### Table: `curriculum.programme`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `programme_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | NO | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `level` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `degree` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `specialisation` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `duration_years` | `numeric(3,1)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `total_terms` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `sanctioned_intake` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.regulation`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `regulation_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `effective_from_admission_year` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `effective_to_admission_year` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `approved_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `approving_body` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `superseded_by` | `uuid` | YES | - | curriculum.regulation(id) | `INTERNAL` | `ALLOW` |
| `document_ref` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.regulation_norm`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `regulation_norm_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `regulation_id` | `uuid` | NO | - | curriculum.regulation(id) | `INTERNAL` | `ALLOW` |
| `programme_id` | `uuid` | YES | - | curriculum.programme(id) | `INTERNAL` | `ALLOW` |
| `course_category` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `min_credits` | `numeric(5,1)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `max_credits` | `numeric(5,1)` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.batch`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `batch_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `programme_id` | `uuid` | NO | - | curriculum.programme(id) | `INTERNAL` | `ALLOW` |
| `regulation_id` | `uuid` | NO | - | curriculum.regulation(id) | `INTERNAL` | `ALLOW` |
| `admission_year` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `label` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `expected_graduation_year` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.section`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `section_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `batch_id` | `uuid` | NO | - | curriculum.batch(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `year_of_study` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `strength` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `class_advisor_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.lab_batch`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lab_batch_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `section_id` | `uuid` | NO | - | curriculum.section(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `strength` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `owning_department_id` | `uuid` | NO | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `short_title` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course_version`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_version_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_id` | `uuid` | NO | - | curriculum.course(id) | `INTERNAL` | `ALLOW` |
| `regulation_id` | `uuid` | NO | - | curriculum.regulation(id) | `INTERNAL` | `ALLOW` |
| `programme_id` | `uuid` | NO | - | curriculum.programme(id) | `INTERNAL` | `ALLOW` |
| `course_code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `term_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `year_of_study` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `course_category` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `course_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_elective` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `elective_group` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `credits` | `numeric(4,1)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `lecture_hours` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `tutorial_hours` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `practical_hours` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `total_contact_hours` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `internal_max_marks` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `external_max_marks` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `pass_min_internal` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `pass_min_external` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `pass_min_total` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `syllabus_document_ref` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course_prerequisite`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `prerequisite_course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `prerequisite_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course_unit`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_unit_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `unit_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `description` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `notional_hours` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course_topic`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_topic_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_unit_id` | `uuid` | NO | - | curriculum.course_unit(id) | `INTERNAL` | `ALLOW` |
| `seq_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `parent_topic_id` | `uuid` | YES | - | curriculum.course_topic(id) | `INTERNAL` | `ALLOW` |
| `notional_hours` | `numeric(3,1)` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course_outcome`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_outcome_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `co_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `statement` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `bloom_level` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `target_level` | `numeric(3,2)` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.unit_outcome_map`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_unit_id` | `uuid` | NO | - | curriculum.course_unit(id) | `INTERNAL` | `ALLOW` |
| `course_outcome_id` | `uuid` | NO | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.programme_outcome`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `programme_outcome_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `programme_id` | `uuid` | NO | - | curriculum.programme(id) | `INTERNAL` | `ALLOW` |
| `regulation_id` | `uuid` | NO | - | curriculum.regulation(id) | `INTERNAL` | `ALLOW` |
| `outcome_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `outcome_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `statement` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `target_level` | `numeric(3,2)` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.co_po_map`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_outcome_id` | `uuid` | NO | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |
| `programme_outcome_id` | `uuid` | NO | - | curriculum.programme_outcome(id) | `INTERNAL` | `ALLOW` |
| `strength` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `justification` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `curriculum.course_book`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_book_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `book_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `authors` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `publisher` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `edition` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `isbn` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `year` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `url` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `seq_no` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |



### Schema: `academics`

*Course offerings, student registrations, faculty allocations, timetables, and class sessions.*

#### Table: `academics.course_offering`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_offering_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `section_id` | `uuid` | NO | - | curriculum.section(id) | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | NO | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `enrolled_count` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `delivery_mode` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.student_registration`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_registration_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `registration_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `attempt_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `registered_on` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.faculty_allocation`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `faculty_allocation_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `faculty_id` | `uuid` | NO | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `lab_batch_id` | `uuid` | YES | - | curriculum.lab_batch(id) | `INTERNAL` | `ALLOW` |
| `role` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `load_share` | `numeric(4,3)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `proposed_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `match_score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `match_rationale` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `override_reason` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `valid_from` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `valid_to` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.time_slot`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `time_slot_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `day_of_week` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `period_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `start_time` | `time` | NO | - | - | `INTERNAL` | `ALLOW` |
| `end_time` | `time` | NO | - | - | `INTERNAL` | `ALLOW` |
| `slot_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.timetable_version`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `timetable_version_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | YES | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `version_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `effective_from` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `effective_to` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `generated_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `solver_stats` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `published_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |


#### Table: `academics.timetable_entry`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `timetable_entry_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `timetable_version_id` | `uuid` | NO | - | academics.timetable_version(id) | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `time_slot_id` | `uuid` | NO | - | academics.time_slot(id) | `INTERNAL` | `ALLOW` |
| `room_id` | `uuid` | YES | - | core.room(id) | `INTERNAL` | `ALLOW` |
| `faculty_id` | `uuid` | NO | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `lab_batch_id` | `uuid` | YES | - | curriculum.lab_batch(id) | `INTERNAL` | `ALLOW` |
| `duration_slots` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.timetable_clash`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `timetable_clash_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `timetable_version_id` | `uuid` | NO | - | academics.timetable_version(id) | `INTERNAL` | `ALLOW` |
| `clash_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `severity` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `description` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `entry_refs` | `uuid[]` | YES | - | - | `INTERNAL` | `ALLOW` |
| `resolved` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.lesson_plan`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lesson_plan_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `prepared_by_faculty_id` | `uuid` | NO | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `total_planned_sessions` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `buffer_sessions` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.lesson_plan_session`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lesson_plan_session_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `lesson_plan_id` | `uuid` | NO | - | academics.lesson_plan(id) | `INTERNAL` | `ALLOW` |
| `seq_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `planned_date` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `course_topic_id` | `uuid` | YES | - | curriculum.course_topic(id) | `INTERNAL` | `ALLOW` |
| `course_unit_id` | `uuid` | YES | - | curriculum.course_unit(id) | `INTERNAL` | `ALLOW` |
| `course_outcome_id` | `uuid` | YES | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |
| `teaching_method` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `resource_ref` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.class_session`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `class_session_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `session_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `time_slot_id` | `uuid` | YES | - | academics.time_slot(id) | `INTERNAL` | `ALLOW` |
| `faculty_id` | `uuid` | NO | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `room_id` | `uuid` | YES | - | core.room(id) | `INTERNAL` | `ALLOW` |
| `lab_batch_id` | `uuid` | YES | - | curriculum.lab_batch(id) | `INTERNAL` | `ALLOW` |
| `session_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `lesson_plan_session_id` | `uuid` | YES | - | academics.lesson_plan_session(id) | `INTERNAL` | `ALLOW` |
| `topic_covered` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `substituted_for_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `marked_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.topic_progress`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `topic_progress_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `course_topic_id` | `uuid` | NO | - | curriculum.course_topic(id) | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `completed_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `class_session_id` | `uuid` | YES | - | academics.class_session(id) | `INTERNAL` | `ALLOW` |
| `remarks` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `academics.coverage_snapshot`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `coverage_snapshot_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `as_of_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `planned_sessions_to_date` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `conducted_sessions` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `planned_topics_to_date` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `completed_topics` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `coverage_pct` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `variance_pct` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `recovery_sessions_needed` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `computed_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |



### Schema: `attendance`

*Class session attendance records, leave applications, daily tracking, and summaries.*

#### Table: `attendance.attendance_record`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attendance_record_id` | `uuid` | NO | - | - | `INTERNAL` | `ALLOW` |
| `class_session_id` | `uuid` | NO | - | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | - | `INTERNAL` | `ALLOW` |
| `session_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `marked_by_user_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `marked_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `source` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `corrected_from` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `correction_reason` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `attendance.attendance_record_2026`
*Partition table of `attendance.attendance_record` (Values: `FROM ('2026-01-01') TO ('2027-01-01')`)*

#### Table: `attendance.attendance_record_2027`
*Partition table of `attendance.attendance_record` (Values: `FROM ('2027-01-01') TO ('2028-01-01')`)*

#### Table: `attendance.student_leave`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_leave_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `leave_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `from_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `to_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `reason` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evidence_ref` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `attendance.attendance_summary`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `True`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attendance_summary_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | YES | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `as_of_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `classes_held` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `classes_attended` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `on_duty_count` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `excused_count` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `raw_pct` | `numeric(5,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `adjusted_pct` | `numeric(5,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `trend_slope` | `numeric(6,3)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `projected_end_pct` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `band` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `risk_level` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `computed_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `agent_run_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `attendance.condonation`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `condonation_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `attendance_pct` | `numeric(5,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `category` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `fee_paid` | `boolean` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `attendance.ingestion_batch`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ingestion_batch_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `source` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `file_ref` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `department_id` | `uuid` | YES | - | core.department(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | YES | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `row_count` | `integer` | YES | - | - | `INTERNAL` | `ALLOW` |
| `accepted_count` | `integer` | YES | - | - | `INTERNAL` | `ALLOW` |
| `rejected_count` | `integer` | YES | - | - | `INTERNAL` | `ALLOW` |
| `validation_report` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `received_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `processed_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |



### Schema: `assessment`

*Assessment definitions, student component marks, internal marks, and course results.*

#### Table: `assessment.assessment_type`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assessment_type_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `category` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `default_max_marks` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `counts_toward_internal` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.assessment`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assessment_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `assessment_type_id` | `uuid` | NO | - | assessment.assessment_type(id) | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `sequence_no` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `max_marks` | `numeric(6,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `weightage` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `conducted_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `syllabus_scope` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `entry_due_date` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.question_bank_item`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `question_bank_item_id` | `uuid` | NO | PK | - | `SENSITIVE` | `ROLE_SCOPED` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `course_unit_id` | `uuid` | YES | - | curriculum.course_unit(id) | `INTERNAL` | `ALLOW` |
| `course_outcome_id` | `uuid` | YES | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |
| `question_text` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `answer_key` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `marks` | `numeric(5,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `bloom_level` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `difficulty` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `question_type` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `origin` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `validation_status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `validated_by_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `validated_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `times_used` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `last_used_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `contributed_by_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |


#### Table: `assessment.paper_blueprint`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `paper_blueprint_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | YES | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `assessment_type_id` | `uuid` | NO | - | assessment.assessment_type(id) | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `total_marks` | `numeric(6,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `duration_minutes` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `structure` | `jsonb` | NO | - | - | `INTERNAL` | `ALLOW` |
| `unit_distribution` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `co_distribution` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `bloom_distribution` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `difficulty_distribution` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.question_paper`
- **Purpose:** Secure examination content and malpractice investigations.
- **Access Classification:** `DENY_GENERAL_ANALYTICS` | **Sensitivity:** `HIGHLY_SENSITIVE` | **RLS Enabled:** `True`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `question_paper_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `assessment_id` | `uuid` | YES | - | assessment.assessment(id) | `INTERNAL` | `ALLOW` |
| `exam_schedule_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `paper_blueprint_id` | `uuid` | YES | - | assessment.paper_blueprint(id) | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `version_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `set_code` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `generated_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `setter_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `moderator_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `sensitivity` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `access_opens_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `access_closes_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.paper_question`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `paper_question_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `question_paper_id` | `uuid` | NO | - | assessment.question_paper(id) | `INTERNAL` | `ALLOW` |
| `question_bank_item_id` | `uuid` | YES | - | assessment.question_bank_item(id) | `SENSITIVE` | `ROLE_SCOPED` |
| `section_code` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `question_no` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `sub_question_of` | `uuid` | YES | - | assessment.paper_question(id) | `INTERNAL` | `ALLOW` |
| `question_text` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `marks` | `numeric(5,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `course_outcome_id` | `uuid` | YES | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |
| `course_unit_id` | `uuid` | YES | - | curriculum.course_unit(id) | `INTERNAL` | `ALLOW` |
| `bloom_level` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_optional` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `choice_group` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.paper_quality_review`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `paper_quality_review_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `question_paper_id` | `uuid` | NO | - | assessment.question_paper(id) | `INTERNAL` | `ALLOW` |
| `reviewed_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `reviewed_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `blueprint_compliance` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `repetition_findings` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `issues` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `overall_verdict` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `moderator_action` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.student_assessment_mark`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_assessment_mark_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `assessment_id` | `uuid` | NO | - | assessment.assessment(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `marks_obtained` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_absent` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_malpractice` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `entered_by_user_id` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `entered_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_locked` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.student_question_mark`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `student_question_mark_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `paper_question_id` | `uuid` | NO | - | assessment.paper_question(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `marks_obtained` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `attempted` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.mark_change_log`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mark_change_log_id` | `bigserial` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_assessment_mark_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | - | `INTERNAL` | `ALLOW` |
| `old_marks` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `new_marks` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `reason` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `changed_by_user_id` | `uuid` | NO | - | - | `INTERNAL` | `ALLOW` |
| `approved_by_user_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `changed_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.internal_mark`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `True`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `internal_mark_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `components` | `jsonb` | NO | - | - | `INTERNAL` | `ALLOW` |
| `formula_version` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `computed_marks` | `numeric(6,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `max_marks` | `numeric(6,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_provisional` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `published_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `finalised_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `finalised_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |


#### Table: `assessment.mark_anomaly`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mark_anomaly_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | YES | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `assessment_id` | `uuid` | YES | - | assessment.assessment(id) | `INTERNAL` | `ALLOW` |
| `anomaly_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `detail` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `severity` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `detected_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `detected_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `resolution_note` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.course_result`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `course_result_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | YES | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `attempt_no` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `exam_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `internal_marks` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `external_marks` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `total_marks` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `max_marks` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `grade` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `grade_point` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `credits` | `numeric(4,1)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `result_status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `published_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.term_result`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `term_result_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `credits_registered` | `numeric(5,1)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `credits_earned` | `numeric(5,1)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `sgpa` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `cgpa` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `backlog_count` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `promotion_status` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `published_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `assessment.backlog`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `backlog_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | NO | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `origin_term_id` | `uuid` | NO | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `attempts_made` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `attempts_remaining` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `cleared_in_term_id` | `uuid` | YES | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `cleared_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |



### Schema: `outcomes`

*Outcome-based education (OBE) attainment rubrics, calculation runs, and CO/PO traces.*

#### Table: `outcomes.attainment_rubric`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attainment_rubric_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `programme_id` | `uuid` | YES | - | curriculum.programme(id) | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `version` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `threshold_pct` | `numeric(5,2)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `level_bands` | `jsonb` | NO | - | - | `INTERNAL` | `ALLOW` |
| `direct_weight` | `numeric(4,3)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `indirect_weight` | `numeric(4,3)` | NO | - | - | `INTERNAL` | `ALLOW` |
| `effective_from` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `effective_to` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `outcomes.attainment_run`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attainment_run_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `attainment_rubric_id` | `uuid` | NO | - | outcomes.attainment_rubric(id) | `INTERNAL` | `ALLOW` |
| `run_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `run_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `input_assessment_ids` | `uuid[]` | YES | - | - | `INTERNAL` | `ALLOW` |
| `student_count` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `outcomes.co_attainment`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `co_attainment_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `attainment_run_id` | `uuid` | NO | - | outcomes.attainment_run(id) | `INTERNAL` | `ALLOW` |
| `course_outcome_id` | `uuid` | NO | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |
| `students_evaluated` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `students_attaining` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `attaining_pct` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `direct_level` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `indirect_level` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `final_level` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `target_level` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `gap` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `contributing_questions` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `outcomes.po_attainment`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `po_attainment_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `programme_outcome_id` | `uuid` | NO | - | curriculum.programme_outcome(id) | `INTERNAL` | `ALLOW` |
| `batch_id` | `uuid` | NO | - | curriculum.batch(id) | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | YES | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `computed_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `contributing_co_count` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `weighted_level` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `target_level` | `numeric(4,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `contributing_runs` | `uuid[]` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |


#### Table: `outcomes.indirect_feedback`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `indirect_feedback_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `course_offering_id` | `uuid` | NO | - | academics.course_offering(id) | `INTERNAL` | `ALLOW` |
| `course_outcome_id` | `uuid` | NO | - | curriculum.course_outcome(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | YES | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `rating` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `submitted_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `outcomes.attainment_action`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attainment_action_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `co_attainment_id` | `uuid` | NO | - | outcomes.co_attainment(id) | `INTERNAL` | `ALLOW` |
| `gap_analysis` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `probable_cause` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `action_proposed` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `owner_faculty_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `target_term_id` | `uuid` | YES | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `outcome_note` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |



### Schema: `placement`

*Corporate partners, job openings, placement drives, student offers, and internships.*

#### Table: `placement.company`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `company_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `sector` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `website` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `tier` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `hr_contact_name` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `hr_contact_email` | `text` | YES | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `hr_contact_phone` | `text` | YES | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `industry_partner_id` | `uuid` | YES | - | engagement.industry_partner(id) | `INTERNAL` | `ALLOW` |
| `alumni_connect_person_id` | `uuid` | YES | - | people.person(id) | `INTERNAL` | `ALLOW` |


#### Table: `placement.job_opening`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `job_opening_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `company_id` | `uuid` | NO | - | placement.company(id) | `INTERNAL` | `ALLOW` |
| `academic_year_id` | `uuid` | NO | - | core.academic_year(id) | `INTERNAL` | `ALLOW` |
| `role_title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `opening_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `job_description` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `required_skills` | `text[]` | YES | - | - | `INTERNAL` | `ALLOW` |
| `preferred_skills` | `text[]` | YES | - | - | `INTERNAL` | `ALLOW` |
| `eligibility` | `jsonb` | NO | - | - | `INTERNAL` | `ALLOW` |
| `ctc_min` | `numeric(12,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `ctc_max` | `numeric(12,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `locations` | `text[]` | YES | - | - | `INTERNAL` | `ALLOW` |
| `positions_open` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `drive_date` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `application_deadline` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.drive_application`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `drive_application_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `job_opening_id` | `uuid` | NO | - | placement.job_opening(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `applied_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `match_score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `match_reason` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `current_round` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.offer`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `offer_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `company_id` | `uuid` | NO | - | placement.company(id) | `INTERNAL` | `ALLOW` |
| `job_opening_id` | `uuid` | YES | - | placement.job_opening(id) | `INTERNAL` | `ALLOW` |
| `role_title` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `ctc` | `numeric(12,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `location` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `offer_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_ppo` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `joining_date` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.readiness_assessment`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `readiness_assessment_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `assessed_on` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `dimension` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `max_score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evidence` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `computed_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.readiness_summary`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `readiness_summary_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `assessed_on` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `overall_score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `readiness_band` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `qualifying_company_count` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `binding_constraint` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `preparation_plan` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.internship`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `internship_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | NO | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `company_id` | `uuid` | YES | - | placement.company(id) | `INTERNAL` | `ALLOW` |
| `company_name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `domain` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `from_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `to_date` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `mode` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `stipend` | `numeric(10,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `legitimacy_verified` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `verified_by_user_id` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `faculty_mentor_id` | `uuid` | YES | - | people.faculty(id) | `INTERNAL` | `ALLOW` |
| `industry_supervisor` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_credit_bearing` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `course_version_id` | `uuid` | YES | - | curriculum.course_version(id) | `INTERNAL` | `ALLOW` |
| `final_grade` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `converted_to_ppo` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.internship_evaluation`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `internship_evaluation_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `internship_id` | `uuid` | NO | - | placement.internship(id) | `INTERNAL` | `ALLOW` |
| `evaluator_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `evaluation_stage` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `max_score` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `criteria_scores` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `remarks` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evaluated_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.alumni`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `alumni_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `student_id` | `uuid` | YES | - | people.student(id) | `INTERNAL` | `ALLOW` |
| `programme_id` | `uuid` | YES | - | curriculum.programme(id) | `INTERNAL` | `ALLOW` |
| `graduation_year` | `smallint` | NO | - | - | `INTERNAL` | `ALLOW` |
| `current_organisation` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `current_designation` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `sector` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `location` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `linkedin_url` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `higher_study_institution` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `outcome_category` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `engagement_level` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `contact_consent` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `publicity_consent` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `last_updated_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `updated_via` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `placement.alumni_contribution`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `alumni_contribution_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `alumni_id` | `uuid` | NO | - | placement.alumni(id) | `INTERNAL` | `ALLOW` |
| `contribution_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `description` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `contributed_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `value` | `numeric(12,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `acknowledged` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |



### Schema: `quality`

*IQAC KPI definitions, periodic measurements, accreditation metrics, and feedback.*

#### Table: `quality.kpi_definition`
- **Purpose:** Public institutional and curricular reference metadata.
- **Access Classification:** `ALLOW` | **Sensitivity:** `PUBLIC_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `kpi_definition_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `domain` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `definition` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `formula` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `unit` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source_query` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `target_value` | `numeric(14,4)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `direction` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `frequency` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `framework_mapping` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `owner_role_id` | `uuid` | YES | - | identity.role(id) | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `quality.kpi_value`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `kpi_value_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `kpi_definition_id` | `uuid` | NO | - | quality.kpi_definition(id) | `INTERNAL` | `ALLOW` |
| `scope_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `scope_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `period_start` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `period_end` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `value` | `numeric(14,4)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `target_value` | `numeric(14,4)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `previous_value` | `numeric(14,4)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `variance_pct` | `numeric(8,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `trend` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `computed_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `computed_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `validated_by_user_id` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `validated_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `quality.accreditation_criterion`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `accreditation_criterion_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `compliance_framework_id` | `uuid` | NO | - | governance.compliance_framework(id) | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `parent_id` | `uuid` | YES | - | quality.accreditation_criterion(id) | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `weightage` | `numeric(6,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evidence_specification` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `responsible_role_id` | `uuid` | YES | - | identity.role(id) | `INTERNAL` | `ALLOW` |


#### Table: `quality.evidence_item`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `evidence_item_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `accreditation_criterion_id` | `uuid` | YES | - | quality.accreditation_criterion(id) | `INTERNAL` | `ALLOW` |
| `title` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `evidence_type` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `period_start` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `period_end` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `document_ref` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source_schema` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source_table` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `generated_by_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `content_hash` | `text` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `approved_by_user_id` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `approved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `created_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `quality.criterion_readiness`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `criterion_readiness_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `accreditation_criterion_id` | `uuid` | NO | - | quality.accreditation_criterion(id) | `INTERNAL` | `ALLOW` |
| `cycle_label` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `assessed_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `evidence_required` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evidence_present` | `smallint` | YES | - | - | `INTERNAL` | `ALLOW` |
| `readiness_pct` | `numeric(5,2)` | YES | - | - | `INTERNAL` | `ALLOW` |
| `gaps` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `owner_user_id` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `status` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `quality.feedback_instrument`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `feedback_instrument_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `institution_id` | `uuid` | NO | - | core.institution(id) | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `audience` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `purpose` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `term_id` | `uuid` | YES | - | core.term(id) | `INTERNAL` | `ALLOW` |
| `questions` | `jsonb` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_anonymous` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `opens_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `closes_on` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `quality.feedback_response`
- **Purpose:** Core institutional operational analytics; scoped by department, school, or role.
- **Access Classification:** `ALLOW_WITH_ROLE_SCOPE` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `feedback_response_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `feedback_instrument_id` | `uuid` | NO | - | quality.feedback_instrument(id) | `INTERNAL` | `ALLOW` |
| `respondent_token` | `text` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `target_type` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `target_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `answers` | `jsonb` | NO | - | - | `INTERNAL` | `ALLOW` |
| `submitted_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |



### Schema: `identity`

*Application users, roles, permissions, audit trails, and data governance.*

#### Table: `identity.app_user`
- **Purpose:** User authentication credentials. Restricted to authorization engine only.
- **Access Classification:** `RESTRICTED` | **Sensitivity:** `HIGHLY_SENSITIVE` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `user_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | YES | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `username` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `email` | `text` | NO | - | - | `SENSITIVE` | `ROLE_SCOPED` |
| `auth_provider` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_active` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_service_account` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `last_login_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `identity.role`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `role_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `name` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `description` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `is_system` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `identity.permission`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `permission_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `resource` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `action` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `sensitivity` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `identity.role_permission`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `role_id` | `uuid` | NO | - | identity.role(id) | `INTERNAL` | `ALLOW` |
| `permission_id` | `uuid` | NO | - | identity.permission(id) | `INTERNAL` | `ALLOW` |


#### Table: `identity.user_role`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `user_role_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `user_id` | `uuid` | NO | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `role_id` | `uuid` | NO | - | identity.role(id) | `INTERNAL` | `ALLOW` |
| `scope_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `scope_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `valid_from` | `date` | NO | - | - | `INTERNAL` | `ALLOW` |
| `valid_to` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `granted_by` | `uuid` | YES | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |


#### Table: `identity.delegation`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `delegation_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `from_user_id` | `uuid` | NO | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `to_user_id` | `uuid` | NO | - | identity.app_user(id) | `INTERNAL` | `ALLOW` |
| `role_id` | `uuid` | NO | - | identity.role(id) | `INTERNAL` | `ALLOW` |
| `reason` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `valid_from` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `valid_to` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |


#### Table: `identity.audit_log`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `audit_id` | `bigserial` | YES | - | - | `INTERNAL` | `ALLOW` |
| `occurred_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `actor_user_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `actor_role` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `on_behalf_of_agent` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `action` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `object_schema` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `object_table` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `object_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `subject_person_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `before_value` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `after_value` | `jsonb` | YES | - | - | `INTERNAL` | `ALLOW` |
| `request_id` | `uuid` | YES | - | - | `INTERNAL` | `ALLOW` |
| `source_ip` | `inet` | YES | - | - | `INTERNAL` | `ALLOW` |
| `justification` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `identity.audit_log_2026`
*Partition table of `identity.audit_log` (Values: `FROM ('2026-01-01') TO ('2027-01-01')`)*

#### Table: `identity.audit_log_2027`
*Partition table of `identity.audit_log` (Values: `FROM ('2027-01-01') TO ('2028-01-01')`)*

#### Table: `identity.data_request`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `data_request_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `request_type` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `details` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |
| `status` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `raised_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `due_by` | `date` | YES | - | - | `INTERNAL` | `ALLOW` |
| `resolved_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `resolution` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |


#### Table: `identity.consent`
- **Purpose:** Operational and governance metadata restricted to authorized roles.
- **Access Classification:** `ROLE_RESTRICTED` | **Sensitivity:** `INTERNAL_ANALYTICS` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `consent_id` | `uuid` | NO | PK | - | `INTERNAL` | `ALLOW` |
| `person_id` | `uuid` | NO | - | people.person(id) | `INTERNAL` | `ALLOW` |
| `purpose_code` | `text` | NO | - | - | `INTERNAL` | `ALLOW` |
| `is_granted` | `boolean` | NO | - | - | `INTERNAL` | `ALLOW` |
| `granted_at` | `timestamptz` | NO | - | - | `INTERNAL` | `ALLOW` |
| `withdrawn_at` | `timestamptz` | YES | - | - | `INTERNAL` | `ALLOW` |
| `evidence_ref` | `text` | YES | - | - | `INTERNAL` | `ALLOW` |



### Schema: `confidential`

*Medical accommodations, psychological counselling notes, and crisis escalation data.*

#### Table: `confidential.counselling_case`
- **Purpose:** Medical and counselling confidential records. Strictly excluded from general analytics.
- **Access Classification:** `DENY_GENERAL_ANALYTICS` | **Sensitivity:** `HIGHLY_SENSITIVE` | **RLS Enabled:** `True`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `counselling_case_id` | `uuid` | NO | PK | - | `HIGHLY_SENSITIVE` | `DENY` |
| `student_id` | `uuid` | NO | - | people.student(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `referral_source` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `referred_by_user_id` | `uuid` | YES | - | identity.app_user(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `opened_at` | `timestamptz` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `urgency` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `counsellor_user_id` | `uuid` | YES | - | identity.app_user(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `status` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `closed_at` | `timestamptz` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |


#### Table: `confidential.counselling_note`
- **Purpose:** Medical and counselling confidential records. Strictly excluded from general analytics.
- **Access Classification:** `DENY_GENERAL_ANALYTICS` | **Sensitivity:** `HIGHLY_SENSITIVE` | **RLS Enabled:** `True`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `counselling_note_id` | `uuid` | NO | PK | - | `HIGHLY_SENSITIVE` | `DENY` |
| `counselling_case_id` | `uuid` | NO | - | confidential.counselling_case(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `counsellor_user_id` | `uuid` | NO | - | identity.app_user(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `session_at` | `timestamptz` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `note_encrypted` | `bytea` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `next_session_on` | `date` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |


#### Table: `confidential.crisis_escalation`
- **Purpose:** Medical and counselling confidential records. Strictly excluded from general analytics.
- **Access Classification:** `DENY_GENERAL_ANALYTICS` | **Sensitivity:** `HIGHLY_SENSITIVE` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `crisis_escalation_id` | `uuid` | NO | PK | - | `HIGHLY_SENSITIVE` | `DENY` |
| `student_id` | `uuid` | NO | - | people.student(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `counselling_case_id` | `uuid` | YES | - | confidential.counselling_case(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `detected_at` | `timestamptz` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `detected_by` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `channel_used` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `escalated_to_user_id` | `uuid` | NO | - | identity.app_user(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `acknowledged_at` | `timestamptz` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `response_time_seconds` | `integer` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `outcome` | `text` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |


#### Table: `confidential.academic_accommodation`
- **Purpose:** Medical and counselling confidential records. Strictly excluded from general analytics.
- **Access Classification:** `DENY_GENERAL_ANALYTICS` | **Sensitivity:** `HIGHLY_SENSITIVE` | **RLS Enabled:** `False`

| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `academic_accommodation_id` | `uuid` | NO | PK | - | `HIGHLY_SENSITIVE` | `DENY` |
| `student_id` | `uuid` | NO | - | people.student(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `accommodation_type` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `course_offering_id` | `uuid` | YES | - | academics.course_offering(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `valid_from` | `date` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `valid_to` | `date` | YES | - | - | `HIGHLY_SENSITIVE` | `DENY` |
| `approved_by` | `uuid` | YES | - | identity.app_user(id) | `HIGHLY_SENSITIVE` | `DENY` |
| `status` | `text` | NO | - | - | `HIGHLY_SENSITIVE` | `DENY` |

