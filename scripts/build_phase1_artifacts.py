"""
Build Phase 1 Artifacts for Agent 63 – Academic Agent Platform
Generates all documentation, JSON registries, data dictionaries, relationship mappings,
sensitivity classifications, and integration documentation.
"""

import json
import os
import re
from collections import defaultdict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_SQL = os.path.join(ROOT_DIR, 'database', 'schema', 'schema_full.sql')

SCHEMA_DESCRIPTIONS = {
    "core": "Institutional profile, campuses, departments, academic calendar, terms, and physical room assets.",
    "people": "Person supertype, student profiles, faculty records, and staff master data.",
    "identity": "Application users, roles, permissions, audit trails, and data governance.",
    "curriculum": "Programmes, regulations, batches, sections, courses, units, topics, and outcomes (CO/PO).",
    "academics": "Course offerings, student registrations, faculty allocations, timetables, and class sessions.",
    "attendance": "Class session attendance records, leave applications, daily tracking, and summaries.",
    "assessment": "Assessment definitions, student component marks, internal marks, and course results.",
    "exams": "Examination sessions, candidate seat allocations, invigilation, and malpractice records.",
    "outcomes": "Outcome-based education (OBE) attainment rubrics, calculation runs, and CO/PO traces.",
    "research": "Faculty and student publications, grants, patents, citations, and project supervision.",
    "engagement": "Institutional events, industry collaborations, MOUs, and community outreach.",
    "admissions": "Application intake, entrance rank verification, quota allocations, and enrollments.",
    "finance": "Student fee structures, payments, dues tracking, scholarships, and fee heads.",
    "studentlife": "Mentoring relationships, student grievances, clubs, and disciplinary cases.",
    "placement": "Corporate partners, job openings, placement drives, student offers, and internships.",
    "hr": "Faculty workload allocations, performance appraisals, leave balances, and profiles.",
    "governance": "Statutory bodies (BoS, Academic Council, Governing Body), policies, and circulars.",
    "quality": "IQAC KPI definitions, periodic measurements, accreditation metrics, and feedback.",
    "knowledge": "Institutional documentation, policy PDF chunking, and embedding vectors.",
    "agentops": "Agent registry, tool definitions, execution runs, human reviews, and safety monitoring.",
    "confidential": "Medical accommodations, psychological counselling notes, and crisis escalation data."
}

def run_build():
    from parse_full_schema import parse_full_sql
    data = parse_full_sql()

    tables = data["tables"]
    views = data["views"]
    schemas = data["schemas"]
    rls_tables = set(data["rls_tables"])
    policies = data["policies"]
    functions = data["functions"]

    print(f"Building artifacts from {len(schemas)} schemas, {len(tables)} tables, {len(views)} views...")

    def classify_object(schema, name, is_view=False):
        full = f"{schema}.{name}"
        
        # Confidential
        if schema == 'confidential':
            return "DENY_GENERAL_ANALYTICS", "HIGHLY_SENSITIVE", "Medical and counselling confidential records. Strictly excluded from general analytics."
        
        # Exam security
        if full in ['assessment.question_paper', 'exams.question_paper_delivery', 'exams.malpractice_incident']:
            return "DENY_GENERAL_ANALYTICS", "HIGHLY_SENSITIVE", "Secure examination content and malpractice investigations."
        
        # Identity credentials
        if full in ['identity.app_user', 'identity.auth_credential', 'identity.user_session', 'identity.password_reset']:
            return "RESTRICTED", "HIGHLY_SENSITIVE", "User authentication credentials. Restricted to authorization engine only."
        
        # Disciplinary & Grievance
        if full in ['studentlife.disciplinary_case', 'studentlife.grievance']:
            return "ROLE_RESTRICTED", "SENSITIVE", "Disciplinary cases and formal student grievances restricted to authorized committees."
        
        # Finance
        if schema == 'finance':
            return "ROLE_RESTRICTED", "SENSITIVE", "Institutional fee collections, dues, and financial ledgers."
        
        # HR
        if schema == 'hr':
            if full == 'hr.faculty_leave_public':
                return "ALLOW", "PUBLIC_ANALYTICS", "Public faculty leave notice."
            return "ROLE_RESTRICTED", "SENSITIVE", "Faculty appraisal, leave records, and administrative workload."
        
        # Core Institutional Lookups
        if full in ['core.institution', 'core.academic_year', 'core.term', 'core.campus', 'core.department', 'curriculum.programme', 'curriculum.regulation', 'curriculum.course', 'quality.kpi_definition']:
            return "ALLOW", "PUBLIC_ANALYTICS", "Public institutional and curricular reference metadata."
        
        # Primary Academic Analytics Objects
        if schema in ['attendance', 'assessment', 'academics', 'curriculum', 'outcomes', 'people', 'placement', 'quality']:
            return "ALLOW_WITH_ROLE_SCOPE", "INTERNAL_ANALYTICS", "Core institutional operational analytics; scoped by department, school, or role."
        
        # Secondary domains (Research, Engagement, Admissions, Governance, Knowledge, Agentops)
        return "ROLE_RESTRICTED", "INTERNAL_ANALYTICS", "Operational and governance metadata restricted to authorized roles."

    # -------------------------------------------------------------
    # 1. database/schema/college_schema_inventory.json
    # -------------------------------------------------------------
    inventory = {
        "database": {
            "name": "academic_agent_platform",
            "target_database": "college_provided",
            "engine": "postgresql",
            "version_target": "14+",
            "source": "college_supplied_schema",
            "schema_file": "01_foundation.sql / schema_full.sql"
        },
        "statistics": {
            "schema_count": len(schemas),
            "table_count": len(tables),
            "view_count": len(views),
            "function_count": len(functions),
            "rls_enabled_tables": len(rls_tables),
            "policies_count": len(policies)
        },
        "schemas": schemas,
        "tables": [
            {
                "full_name": t["full_name"],
                "schema": t["schema"],
                "table_name": t["table_name"],
                "is_partition": t["is_partition"],
                "parent_table": t.get("parent_table"),
                "column_count": len(t["columns"]),
                "primary_key": t["primary_key"],
                "foreign_key_count": len(t["foreign_keys"]),
                "is_rls_enabled": t["is_rls_enabled"],
                "access_classification": classify_object(t["schema"], t["table_name"])[0],
                "sensitivity": classify_object(t["schema"], t["table_name"])[1]
            }
            for t in tables
        ],
        "views": views,
        "functions": functions,
        "rls_policies": policies
    }

    inv_path = os.path.join(ROOT_DIR, 'database', 'schema', 'college_schema_inventory.json')
    with open(inv_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2)
    print(f"Wrote {inv_path}")

    # -------------------------------------------------------------
    # 2. database/mappings/agent63_schema_registry.json
    # -------------------------------------------------------------
    registry_objects = []

    # Analytical grain definitions
    grain_map = {
        "people.student": "student",
        "people.faculty": "faculty_member",
        "core.department": "department",
        "core.term": "academic_term",
        "curriculum.course": "course",
        "curriculum.course_offering": "course_offering",
        "academics.course_offering": "course_offering (academic class/term)",
        "academics.student_registration": "student_course_enrollment",
        "academics.timetable": "scheduled_slot",
        "academics.class_session": "delivered_class_session",
        "attendance.attendance_record": "student_session_attendance",
        "attendance.attendance_summary": "student_course_term_attendance",
        "assessment.assessment": "assessment_event (midterm/endterm/quiz)",
        "assessment.student_assessment_mark": "student_assessment_component_mark",
        "assessment.internal_mark": "student_course_internal_aggregate",
        "assessment.course_result": "student_course_final_grade",
        "assessment.term_result": "student_semester_gpa",
        "assessment.backlog": "student_course_backlog",
        "outcomes.co_attainment": "course_outcome_attainment",
        "outcomes.po_attainment": "programme_outcome_attainment",
        "placement.drive_application": "student_placement_application",
        "placement.offer": "student_job_offer",
        "placement.readiness_summary": "student_placement_readiness",
        "quality.kpi_definition": "institutional_kpi_metric",
        "quality.kpi_value": "measured_kpi_value_period"
    }

    join_map = {
        "people.student": ["people.person (person_id)", "curriculum.programme (programme_id)", "curriculum.batch (batch_id)", "curriculum.section (section_id)"],
        "academics.course_offering": ["curriculum.course (course_id)", "core.term (term_id)", "core.department (department_id)"],
        "academics.student_registration": ["academics.course_offering (course_offering_id)", "people.student (student_id)"],
        "attendance.attendance_record": ["academics.class_session (class_session_id)", "people.student (student_id)"],
        "attendance.attendance_summary": ["academics.course_offering (course_offering_id)", "people.student (student_id)"],
        "assessment.student_assessment_mark": ["assessment.assessment (assessment_id)", "people.student (student_id)"],
        "assessment.course_result": ["academics.course_offering (course_offering_id)", "people.student (student_id)"],
        "assessment.term_result": ["core.term (term_id)", "people.student (student_id)"],
        "outcomes.co_attainment": ["curriculum.course_outcome (course_outcome_id)", "academics.course_offering (course_offering_id)"],
        "outcomes.po_attainment": ["curriculum.programme_outcome (programme_outcome_id)", "curriculum.batch (batch_id)"],
        "placement.offer": ["placement.job_opening (job_opening_id)", "people.student (student_id)"],
        "quality.kpi_value": ["quality.kpi_definition (kpi_id)", "core.academic_year (academic_year_id)", "core.department (department_id)"]
    }

    for t in tables:
        full_name = t["full_name"]
        schema = t["schema"]
        tname = t["table_name"]
        access, sens, purpose = classify_object(schema, tname)

        # Identify restricted columns
        allowed_cols = []
        restricted_cols = []
        for c in t["columns"]:
            cname = c["name"]
            # Classify PII / secret columns
            if any(k in cname.lower() for k in ['password', 'secret', 'token', 'salt', 'hash', 'aadhar', 'ssn', 'bank', 'account_no']):
                restricted_cols.append(cname)
            elif schema == 'confidential':
                restricted_cols.append(cname)
            else:
                allowed_cols.append(cname)

        registry_objects.append({
            "schema": schema,
            "object": tname,
            "full_name": full_name,
            "object_type": "table",
            "access": access,
            "sensitivity": sens,
            "purpose": purpose,
            "grain": grain_map.get(full_name, f"row of {full_name}"),
            "primary_key": t["primary_key"],
            "foreign_keys": t["foreign_keys"],
            "allowed_columns": allowed_cols,
            "restricted_columns": restricted_cols,
            "recommended_joins": join_map.get(full_name, []),
            "analytics_domains": [schema]
        })

    # Add views to registry
    for v in views:
        v_full = v["view_name"]
        schema = v["schema"]
        vname = v["name"]
        access, sens, purpose = classify_object(schema, vname, is_view=True)
        registry_objects.append({
            "schema": schema,
            "object": vname,
            "full_name": v_full,
            "object_type": "view",
            "access": access,
            "sensitivity": sens,
            "purpose": f"Authoritative analytical view: {vname}",
            "grain": grain_map.get(v_full, f"aggregated view {vname}"),
            "primary_key": [],
            "foreign_keys": [],
            "allowed_columns": ["*"],
            "restricted_columns": [],
            "recommended_joins": v["referenced_tables"],
            "analytics_domains": [schema, "read_layer"]
        })

    registry = {
        "version": "1.0",
        "database_engine": "postgresql",
        "database_version_target": "14+",
        "total_registered_objects": len(registry_objects),
        "access_summary": {
            "ALLOW": len([o for o in registry_objects if o["access"] == "ALLOW"]),
            "ALLOW_WITH_ROLE_SCOPE": len([o for o in registry_objects if o["access"] == "ALLOW_WITH_ROLE_SCOPE"]),
            "ROLE_RESTRICTED": len([o for o in registry_objects if o["access"] == "ROLE_RESTRICTED"]),
            "RESTRICTED": len([o for o in registry_objects if o["access"] == "RESTRICTED"]),
            "DENY_GENERAL_ANALYTICS": len([o for o in registry_objects if o["access"] == "DENY_GENERAL_ANALYTICS"])
        },
        "objects": registry_objects
    }

    reg_path = os.path.join(ROOT_DIR, 'database', 'mappings', 'agent63_schema_registry.json')
    with open(reg_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2)
    print(f"Wrote {reg_path}")

    # -------------------------------------------------------------
    # 3. database/schema/college_data_dictionary.md
    # -------------------------------------------------------------
    dict_md = []
    dict_md.append("# Agent 63 – College Database Data Dictionary")
    dict_md.append("\n> **Authoritative Source:** `01_foundation.sql` / `schema_full.sql` (PostgreSQL 14+)")
    dict_md.append("> **Scale:** 21 Schemas, 225 Tables, 11 Views, 7 RLS Tables, 19 Security Policies\n")
    dict_md.append("## Overview of Institutional Schemas\n")
    dict_md.append("| Schema | Description | Classification | Initial Agent 63 Status |")
    dict_md.append("| :--- | :--- | :--- | :--- |")
    for s in schemas:
        dict_md.append(f"| `{s['schema_name']}` | {s['description']} | `{s['classification']}` | {'ALLOWED (Scoped)' if s['classification'] in ['INTERNAL_ANALYTICS', 'PUBLIC_ANALYTICS'] else 'RESTRICTED' if s['classification'] != 'DENY_GENERAL_ANALYTICS' else 'DENIED'} |")

    dict_md.append("\n---\n")
    dict_md.append("## Core Institutional Analytics Data Dictionary\n")

    # Group tables by schema
    schema_groups = defaultdict(list)
    for t in tables:
        schema_groups[t["schema"]].append(t)

    # Focus deeply on major analytical schemas
    priority_schemas = ['core', 'people', 'curriculum', 'academics', 'attendance', 'assessment', 'outcomes', 'placement', 'quality', 'identity', 'confidential']
    for s_name in priority_schemas:
        dict_md.append(f"\n### Schema: `{s_name}`\n")
        dict_md.append(f"*{SCHEMA_DESCRIPTIONS.get(s_name, '')}*\n")
        
        for t in schema_groups[s_name]:
            dict_md.append(f"#### Table: `{t['full_name']}`")
            if t['is_partition']:
                dict_md.append(f"*Partition table of `{t['parent_table']}` (Values: `{t.get('partition_values')}`)*\n")
                continue
            
            access, sens, purp = classify_object(s_name, t['table_name'])
            dict_md.append(f"- **Purpose:** {purp}")
            dict_md.append(f"- **Access Classification:** `{access}` | **Sensitivity:** `{sens}` | **RLS Enabled:** `{t['is_rls_enabled']}`\n")
            
            dict_md.append("| Column | PostgreSQL Type | Nullable | PK | FK Reference | Sensitivity | Agent 63 Access |")
            dict_md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            
            # map FKs for quick lookup
            col_fks = {}
            for fk in t["foreign_keys"]:
                for fc in fk["from_columns"]:
                    col_fks[fc] = f"{fk['target_table']}({','.join(fk['target_columns'])})"

            for c in t["columns"]:
                cname = c["name"]
                ctype = c["type"]
                cnull = "YES" if c["nullable"] else "NO"
                cpk = "PK" if c["is_primary_key"] else "-"
                cfk = col_fks.get(cname, "-")
                
                # Column sensitivity
                if any(k in cname.lower() for k in ['password', 'secret', 'token', 'hash']):
                    csens = "HIGHLY_SENSITIVE"
                    cacc = "DENY"
                elif s_name == 'confidential':
                    csens = "HIGHLY_SENSITIVE"
                    cacc = "DENY"
                elif any(k in cname.lower() for k in ['aadhar', 'ssn', 'bank', 'phone', 'email', 'salary']):
                    csens = "SENSITIVE"
                    cacc = "ROLE_SCOPED"
                else:
                    csens = "INTERNAL"
                    cacc = "ALLOW"

                dict_md.append(f"| `{cname}` | `{ctype}` | {cnull} | {cpk} | {cfk} | `{csens}` | `{cacc}` |")
            dict_md.append("\n")

    dict_md_path = os.path.join(ROOT_DIR, 'database', 'schema', 'college_data_dictionary.md')
    with open(dict_md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(dict_md))
    print(f"Wrote {dict_md_path}")

    # -------------------------------------------------------------
    # 4. database/schema/college_relationships.md
    # -------------------------------------------------------------
    rel_md = []
    rel_md.append("# Agent 63 – College Database Relationship & Grain Architecture")
    rel_md.append("\n> **Primary Focus:** Documenting authoritative joins, entity cardinalities, and analytical grains.")
    rel_md.append("> **Source:** Inspected PostgreSQL 14+ institutional schema (`01_foundation.sql` / `schema_full.sql`)\n")
    
    rel_md.append("## 1. Central Academic Grain: `academics.course_offering`")
    rel_md.append("In the supplied college database, `academics.course_offering` is the **central operational nexus** for all academic delivery facts.")
    rel_md.append("Every class delivery, attendance record, internal assessment, and faculty allocation connects through `course_offering`.\n")
    rel_md.append("```")
    rel_md.append("                       curriculum.course (What is taught)")
    rel_md.append("                               │")
    rel_md.append("                               ▼")
    rel_md.append("core.term ──────────► academics.course_offering ◄────────── core.department")
    rel_md.append("(When it is taught)            │                            (Who offers it)")
    rel_md.append("                               ├──────────────────────────┐")
    rel_md.append("                               ▼                          ▼")
    rel_md.append("                 academics.student_registration   academics.class_session")
    rel_md.append("                               │                          │")
    rel_md.append("                               ▼                          ▼")
    rel_md.append("                 assessment.course_result        attendance.attendance_record")
    rel_md.append("```\n")

    rel_md.append("## 2. Core Institutional Join Paths\n")
    rel_md.append("### A. Student Enrollment & Academic Progression Path")
    rel_md.append("```sql")
    rel_md.append("-- Trace student from institutional cohort to class registration")
    rel_md.append("people.student (student_id)")
    rel_md.append("  INNER JOIN people.person ON student.person_id = person.person_id")
    rel_md.append("  INNER JOIN curriculum.programme ON student.programme_id = programme.programme_id")
    rel_md.append("  INNER JOIN curriculum.batch ON student.batch_id = batch.batch_id")
    rel_md.append("  LEFT JOIN curriculum.section ON student.current_section_id = section.section_id")
    rel_md.append("  INNER JOIN academics.student_registration ON student.student_id = student_registration.student_id")
    rel_md.append("  INNER JOIN academics.course_offering ON student_registration.course_offering_id = course_offering.course_offering_id")
    rel_md.append("  INNER JOIN curriculum.course ON course_offering.course_id = course.course_id;")
    rel_md.append("```\n")

    rel_md.append("### B. Student Attendance Verification Path")
    rel_md.append("```sql")
    rel_md.append("-- Attendance aggregates connect student to offering and session details")
    rel_md.append("attendance.attendance_summary (summary_id)")
    rel_md.append("  INNER JOIN people.student ON attendance_summary.student_id = student.student_id")
    rel_md.append("  INNER JOIN academics.course_offering ON attendance_summary.course_offering_id = course_offering.course_offering_id")
    rel_md.append("  INNER JOIN core.term ON course_offering.term_id = term.term_id")
    rel_md.append("  INNER JOIN core.department ON course_offering.department_id = department.department_id;")
    rel_md.append("```\n")

    rel_md.append("### C. Examination, Internal Assessment & Results Path")
    rel_md.append("```sql")
    rel_md.append("-- Connect assessment marks to individual students and course offerings")
    rel_md.append("assessment.student_assessment_mark (mark_id)")
    rel_md.append("  INNER JOIN assessment.assessment ON student_assessment_mark.assessment_id = assessment.assessment_id")
    rel_md.append("  INNER JOIN academics.course_offering ON assessment.course_offering_id = course_offering.course_offering_id")
    rel_md.append("  INNER JOIN people.student ON student_assessment_mark.student_id = student.student_id;")
    rel_md.append("```\n")

    rel_md.append("### D. Outcome-Based Education (OBE) Attainment Path")
    rel_md.append("```sql")
    rel_md.append("-- Trace student outcome attainment back to course competencies")
    rel_md.append("outcomes.co_attainment (co_attainment_id)")
    rel_md.append("  INNER JOIN curriculum.course_outcome ON co_attainment.course_outcome_id = course_outcome.course_outcome_id")
    rel_md.append("  INNER JOIN curriculum.co_po_map ON course_outcome.course_outcome_id = co_po_map.course_outcome_id")
    rel_md.append("  INNER JOIN curriculum.programme_outcome ON co_po_map.programme_outcome_id = programme_outcome.programme_outcome_id;")
    rel_md.append("```\n")

    rel_md.append("## 3. Analytical Grains Catalog\n")
    rel_md.append("| Object | Natural Grain | Primary Identifier | Temporal Dimensions | Key Measures |")
    rel_md.append("| :--- | :--- | :--- | :--- | :--- |")
    rel_md.append("| `people.student` | One record per admitted student | `student_id` | `admission_year`, `expected_graduation_year` | Student count |")
    rel_md.append("| `academics.course_offering` | One offering of a course in a specific term | `course_offering_id` | `core.term.academic_year_id` | Registered capacity, session count |")
    rel_md.append("| `academics.student_registration` | One student enrolled in one course offering | `registration_id` | `registered_on` | Enrollment count |")
    rel_md.append("| `attendance.attendance_record` | One student attendance fact per class session | `attendance_record_id` | `session_date` | Present / Absent / Late / On-Duty |")
    rel_md.append("| `attendance.attendance_summary` | Cumulative attendance for a student in an offering | `summary_id` | `term_id` | `attended_sessions`, `total_sessions`, `attendance_pct` |")
    rel_md.append("| `assessment.assessment` | One scheduled assessment component | `assessment_id` | `conducted_on` | `max_marks`, `weightage` |")
    rel_md.append("| `assessment.student_assessment_mark` | Marks earned by one student in one component | `mark_id` | `marked_at` | `marks_obtained`, `is_absent` |")
    rel_md.append("| `assessment.course_result` | Final grade for a student in an offering | `course_result_id` | `published_on` | `total_marks`, `grade_point`, `is_passed` |")
    rel_md.append("| `outcomes.co_attainment` | Attainment score for a CO in an offering | `co_attainment_id` | `calculated_at` | `attainment_level_achieved`, `target_pct` |")
    rel_md.append("| `placement.offer` | One job offer received by a student | `offer_id` | `offered_on` | `ctc_lpa`, `stipend_monthly` |")
    rel_md.append("| `quality.kpi_value` | Periodic measurement of an institutional KPI | `kpi_value_id` | `academic_year_id`, `period_start` | `measured_value`, `target_value` |")

    rel_path = os.path.join(ROOT_DIR, 'database', 'schema', 'college_relationships.md')
    with open(rel_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rel_md))
    print(f"Wrote {rel_path}")

    # -------------------------------------------------------------
    # 5. database/schema/sensitivity-classification.md
    # -------------------------------------------------------------
    sens_md = []
    sens_md.append("# Agent 63 – Data Sensitivity & Classification Policy")
    sens_md.append("\n> **Mandate:** Protect student privacy, institutional security, and statutory confidentiality.")
    sens_md.append("> **Enforcement:** Enforced at Schema Registry, Semantic Layer, and Backend Query Builders.\n")
    
    sens_md.append("## Classification Tiers\n")
    sens_md.append("### 1. `PUBLIC_ANALYTICS`")
    sens_md.append("- **Description:** Institution-wide public facts, academic calendars, curriculum structures, and published regulations.")
    sens_md.append("- **Objects:** `core.institution`, `core.academic_year`, `core.term`, `core.campus`, `curriculum.programme`, `curriculum.course`, `quality.kpi_definition`.")
    sens_md.append("- **Agent 63 Action:** Permitted for all authenticated users without departmental filtering.\n")

    sens_md.append("### 2. `INTERNAL_ANALYTICS`")
    sens_md.append("- **Description:** Aggregated academic performance, cohort statistics, department benchmarks, and placement summaries.")
    sens_md.append("- **Objects:** `attendance.v_current_attendance`, `assessment.v_course_performance`, `outcomes.v_attainment_trace`, `placement.readiness_summary`.")
    sens_md.append("- **Agent 63 Action:** Permitted subject to RBAC role boundaries (Management sees college-wide, HOD sees department).\n")

    sens_md.append("### 3. `ROLE_RESTRICTED`")
    sens_md.append("- **Description:** Detailed operational and administrative data requiring explicit role clearance (e.g. Dean/Principal/IQAC).")
    sens_md.append("- **Objects:** `finance.student_dues`, `hr.faculty_workload`, `exams.exam_session`, `governance.committee_meeting`.")
    sens_md.append("- **Agent 63 Action:** Blocked for general queries; permitted only when requesting user possesses specific verified role.\n")

    sens_md.append("### 4. `SENSITIVE`")
    sens_md.append("- **Description:** Personal identifiable information (PII), disciplinary investigations, and staff appraisals.")
    sens_md.append("- **Objects:** `studentlife.disciplinary_case`, `hr.faculty_appraisal`, `admissions.quota_allocation`.")
    sens_md.append("- **Agent 63 Action:** Masked or withheld from LLM query generation.\n")

    sens_md.append("### 5. `HIGHLY_SENSITIVE` / `DENY_GENERAL_ANALYTICS`")
    sens_md.append("- **Description:** Psychological counselling records, medical notes, exam questions, and authentication credentials.")
    sens_md.append("- **Objects:**")
    sens_md.append("  - `confidential.*` (`counselling_case`, `counselling_note`, `medical_record`, `crisis_escalation`)")
    sens_md.append("  - `assessment.question_paper`")
    sens_md.append("  - `identity.auth_credential`, `identity.app_user` (password hashes, tokens)")
    sens_md.append("- **Agent 63 Action:** **HARD DENY.** Excluded from Agent 63 Schema Registry allowlists. Queries targeting these objects are rejected before execution.\n")

    sens_md.append("## Explicit Column Masking Rules\n")
    sens_md.append("| Table | Column | Risk | Masking / Action |")
    sens_md.append("| :--- | :--- | :--- | :--- |")
    sens_md.append("| `people.person` | `aadhar_number` / `national_id` | Identity theft | EXCLUDED from query projection |")
    sens_md.append("| `people.person` | `phone`, `email` | Privacy leak | Masked (`XXXXX-1234`) in student exports |")
    sens_md.append("| `finance.fee_payment` | `transaction_reference` | Financial PII | Withheld from conversational answers |")
    sens_md.append("| `confidential.*` | ALL COLUMNS | Statutory medical confidentiality | NEVER ACCESSED OR JOINED |")

    sens_path = os.path.join(ROOT_DIR, 'database', 'schema', 'sensitivity-classification.md')
    with open(sens_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sens_md))
    print(f"Wrote {sens_path}")

    # -------------------------------------------------------------
    # 6. database/schema/data-quality-considerations.md
    # -------------------------------------------------------------
    dq_md = []
    dq_md.append("# Agent 63 – College Data Quality & Analytical Quirks Analysis")
    dq_md.append("\n> **Analysis:** Observations derived from physical schema inspection of `schema_full.sql`.")
    dq_md.append("> **Purpose:** Guiding the Phase 4 Semantic Layer and Phase 8 Result Validator to avoid incorrect calculations.\n")

    dq_md.append("## 1. Table Partitioning Behavior (`attendance` and `identity`)")
    dq_md.append("- `attendance.attendance_record` is partitioned by range (`session_date`), e.g., `attendance_record_2026`, `attendance_record_2027`.")
    dq_md.append("- `identity.audit_log` is partitioned by range (`occurred_at`), e.g., `audit_log_2026`, `audit_log_2027`.")
    dq_md.append("- **Analytical Impact:** Query planners must include explicit date bounds in `WHERE` clauses to enable partition pruning and prevent expensive full-table scans across multi-year attendance tables.\n")

    dq_md.append("## 2. Attendance Adjustment & Condonation (`attendance.attendance_summary`)")
    dq_md.append("- The schema contains both raw `attendance_pct` and `adjusted_attendance_pct` (accounting for medical leaves and official duty leaves `student_leave`).")
    dq_md.append("- **Rule for Semantic Layer:** Inquiries asking for 'Official Attendance' must query `adjusted_attendance_pct`, while inquiries asking for 'Physical Attendance' query `attendance_pct`.\n")

    dq_md.append("## 3. Backlogs & Multi-Attempt Assessments (`assessment.backlog`)")
    dq_md.append("- Students who fail an end-term examination reappear in subsequent terms (`assessment.backlog`).")
    dq_md.append("- **Analytical Impact:** Calculating 'Pass Percentage' requires distinguishing between **First-Attempt Pass Rate** (cohort intake success) and **Final Graduating Pass Rate** (including backlog clearances).\n")

    dq_md.append("## 4. Multiple Course Offerings per Term (`academics.course_offering`)")
    dq_md.append("- A single course (e.g., *Data Structures*) may have 4 distinct offerings across sections A, B, C, and D in a single term.")
    dq_md.append("- **Analytical Impact:** Aggregating marks or attendance across a course requires grouping by `course_id` across offerings, rather than assuming a 1-to-1 relationship between course and offering.\n")

    dq_md.append("## 5. Nullable Analytical Dimensions")
    dq_md.append("- `core.calendar_event.department_id` is nullable (NULL denotes an institution-wide event, whereas non-NULL denotes a department-specific holiday).")
    dq_md.append("- `people.faculty.resigned_on` is nullable (NULL denotes actively serving faculty).")
    dq_md.append("- **Analytical Impact:** Missing `IS NULL` filters on `resigned_on` would incorrectly inflate faculty-student ratio calculations.\n")

    dq_path = os.path.join(ROOT_DIR, 'database', 'schema', 'data-quality-considerations.md')
    with open(dq_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(dq_md))
    print(f"Wrote {dq_path}")

    # -------------------------------------------------------------
    # 7. database/mappings/initial_analytics_scope.md
    # -------------------------------------------------------------
    scope_md = []
    scope_md.append("# Agent 63 – Initial Analytics Scope Specification")
    scope_md.append("\n> **Status:** Defined in Phase 1 for Semantic Layer (Phase 4) and Intent Parser (Phase 6).\n")
    scope_md.append("## Priority Analytics Domains (Phase 1 Approved Scope)")
    scope_md.append("The initial release of Agent 63 prioritizes nine core operational domains:\n")
    scope_md.append("1. **`core`**: Institutional metadata, campuses, departments, terms, academic years, and classrooms.")
    scope_md.append("2. **`people`**: Student demographics, faculty rosters, staff assignments, and profiles (`v_student_profile`).")
    scope_md.append("3. **`curriculum`**: Programmes, regulations, batches, sections, courses, syllabi, and outcome definitions (CO/PO).")
    scope_md.append("4. **`academics`**: Course offerings, student registrations, timetable delivery, lesson plans, and class progress.")
    scope_md.append("5. **`attendance`**: Daily session attendance, student leaves, and aggregate attendance summaries (`v_current_attendance`).")
    scope_md.append("6. **`assessment`**: Component assessments, question marks, internal marks, course grades, and term results (`v_course_performance`).")
    scope_md.append("7. **`outcomes`**: Attainment rubrics, CO/PO calculation runs, and traceability traces (`v_attainment_trace`).")
    scope_md.append("8. **`placement`**: Placement drives, company visits, job applications, offers, internships, and readiness scores.")
    scope_md.append("9. **`quality`**: IQAC KPI definitions, periodic attainment values, and accreditation metrics (`v_kpi_latest`).\n")

    scope_md.append("## Deferred / Restricted Domains (Future Phases)")
    scope_md.append("- **`finance`**: Restricted fee transactions, ledger entries, and student dues.")
    scope_md.append("- **`hr`**: Faculty appraisals, payroll metadata, and workload calculations.")
    scope_md.append("- **`studentlife`**: Disciplinary cases and student grievances (high sensitivity).")
    scope_md.append("- **`research`**, **`engagement`**, **`admissions`**, **`governance`**: Slated for Phase 12 executive dashboard integrations.")
    scope_md.append("- **`identity`**: Restricted exclusively to user authorization, role verification, and audit logging. **Never directly queryable as an analytics source.**\n")

    scope_md.append("## Strictly Denied Domain")
    scope_md.append("- **`confidential`**: Complete exclusion. Medical records, counselling cases, and crisis escalation data will NEVER be queried or exposed.\n")

    scope_path = os.path.join(ROOT_DIR, 'database', 'mappings', 'initial_analytics_scope.md')
    with open(scope_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(scope_md))
    print(f"Wrote {scope_path}")

    # -------------------------------------------------------------
    # 8. database/documentation/read-only-integration.md
    # -------------------------------------------------------------
    ro_md = []
    ro_md.append("# Agent 63 – Read-Only Database Integration Architecture")
    ro_md.append("\n> **Status:** Scaffolding Documented in Phase 1 (Connection deferred to runtime phases)\n")
    ro_md.append("## 1. Connection Philosophy & Least Privilege")
    ro_md.append("Agent 63 executes queries strictly via a dedicated PostgreSQL read-only database role. The database user must have zero write privileges:\n")
    ro_md.append("```sql")
    ro_md.append("-- Recommended PostgreSQL setup for Agent 63 read-only user")
    ro_md.append("CREATE ROLE agent63_readonly WITH LOGIN PASSWORD 'CHANGE_IN_PRODUCTION';")
    ro_md.append("GRANT CONNECT ON DATABASE academic_agent_platform TO agent63_readonly;")
    ro_md.append("GRANT USAGE ON SCHEMA core, people, curriculum, academics, attendance, assessment, outcomes, placement, quality TO agent63_readonly;")
    ro_md.append("GRANT SELECT ON ALL TABLES IN SCHEMA core, people, curriculum, academics, attendance, assessment, outcomes, placement, quality TO agent63_readonly;")
    ro_md.append("ALTER DEFAULT PRIVILEGES IN SCHEMA core, people, curriculum, academics, attendance, assessment, outcomes, placement, quality GRANT SELECT ON TABLES TO agent63_readonly;")
    ro_md.append("REVOKE ALL ON SCHEMA confidential FROM agent63_readonly;")
    ro_md.append("REVOKE ALL ON TABLE assessment.question_paper FROM agent63_readonly;")
    ro_md.append("```\n")

    ro_md.append("## 2. Resource Containment & Timeout Controls")
    ro_md.append("- **Statement Timeout:** Default `5000ms` (5 seconds). Any query running longer than 5 seconds is terminated by PostgreSQL (`SET statement_timeout = '5000'`).")
    ro_md.append("- **Connection Pool:** Managed via SQLAlchemy Core with a maximum of 10 connections (`pool_size=10, max_overflow=5`).")
    ro_md.append("- **Read-Only Transaction State:** Connections explicitly set `default_transaction_read_only = on`.\n")

    ro_md.append("## 3. Current Connection Status")
    ro_md.append("- **Schema Definition Status:** Inspected and fully mapped (`schema_full.sql`).")
    ro_md.append("- **Live Database Connection Status:** **NOT CONFIGURED IN PHASE 1.**")
    ro_md.append("- **Populated Production Data Availability:** **UNKNOWN / NOT CONNECTED.**")
    ro_md.append("- Real student records have NOT been accessed; Phase 1 establishes the structural catalog only.\n")

    ro_path = os.path.join(ROOT_DIR, 'database', 'documentation', 'read-only-integration.md')
    with open(ro_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ro_md))
    print(f"Wrote {ro_path}")

    # -------------------------------------------------------------
    # 9. database/documentation/database-security-integration.md
    # -------------------------------------------------------------
    sec_int_md = []
    sec_int_md.append("# Agent 63 – Database Security & RLS Integration Analysis")
    sec_int_md.append("\n> **Inspection:** Analysis of Row Level Security (RLS) and Audit Mechanisms in `schema_full.sql`.\n")
    sec_int_md.append("## 1. Discovered Row Level Security (RLS) Tables")
    sec_int_md.append("The college schema explicitly enables RLS on 7 sensitive tables:\n")
    for r in sorted(list(rls_tables)):
        sec_int_md.append(f"- `{r}`")
    sec_int_md.append("\n## 2. Discovered Security Policies")
    sec_int_md.append("| Table | Policy Name | Command | Target Roles | Using Expression |")
    sec_int_md.append("| :--- | :--- | :--- | :--- | :--- |")
    for p in policies:
        sec_int_md.append(f"| `{p['table_name']}` | `{p['policy_name']}` | `{p['for_command']}` | `{p['roles']}` | `{p['using_expression'][:60]}...` |")

    sec_int_md.append("\n## 3. Built-in Authorization Helper Functions")
    sec_int_md.append("The college database defines modular PostgreSQL functions for context-aware security:\n")
    for f in functions:
        sec_int_md.append(f"- **`{f['function_name']}({f['arguments']})`** $\\rightarrow$ `{f['return_type']}`")

    sec_int_md.append("\n## 4. Integration Strategy for Agent 63")
    sec_int_md.append("Agent 63's future authorization layer (Phase 5) will complement rather than circumvent database security:")
    sec_int_md.append("1. **Session Variables:** Before executing queries, the query executor sets PostgreSQL session variables corresponding to user claims (e.g., `SET LOCAL app.user_id = '...'`, `SET LOCAL app.department_id = '...'`).")
    sec_int_md.append("2. **Dual Enforcement:** Scopes are injected in Python SQL generation AND verified by database RLS policies for defense-in-depth.")
    sec_int_md.append("3. **Zero Mutation Triggers:** Audit triggers (`core.set_row_audit()`) will never be fired because Agent 63 operates exclusively with `SELECT` queries.")

    sec_int_path = os.path.join(ROOT_DIR, 'database', 'documentation', 'database-security-integration.md')
    with open(sec_int_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sec_int_md))
    print(f"Wrote {sec_int_path}")

    print("Phase 1 Artifacts successfully generated.")

if __name__ == '__main__':
    run_build()
