"""
Master Schema Generator for Agent 63 Phase 1
Parses database/schema/schema_full.sql and builds:
1. database/schema/college_schema_inventory.json
2. database/schema/college_data_dictionary.md
3. database/schema/college_relationships.md
4. database/schema/sensitivity-classification.md
5. database/schema/data-quality-considerations.md
6. database/mappings/agent63_schema_registry.json
7. database/mappings/initial_analytics_scope.md
8. database/documentation/read-only-integration.md
9. database/documentation/database-security-integration.md
"""

import json
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SQL_FILE = os.path.join(ROOT_DIR, 'database', 'schema', 'schema_full.sql')

def parse_full_sql():
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Schemas
    schema_matches = re.findall(r'CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)\s*;(?:\s*--\s*(.*))?', content, re.IGNORECASE)
    schemas = []
    schema_descriptions = {
        "core": "Institutional profile, campuses, departments, academic calendar, terms, and physical room assets.",
        "people": "Supertype person registry, student profiles, faculty records, and staff master data.",
        "identity": "Application users, roles, permissions, audit trails, data requests, and session tokens.",
        "curriculum": "Academic programmes, regulations, batches, sections, courses, units, topics, and outcomes (CO/PO).",
        "academics": "Course offerings, student registrations, faculty allocations, timetables, lesson plans, class sessions, and syllabus coverage.",
        "attendance": "Class session attendance records, leave applications, daily tracking, and aggregated attendance summaries.",
        "assessment": "Assessment definitions, student question marks, component marks, internal marks, course results, term results, backlogs, and question papers.",
        "exams": "Examination sessions, candidate seat allocations, invigilation duties, paper delivery tracking, and malpractice incidents.",
        "outcomes": "Outcome-based education (OBE) attainment rubrics, calculation runs, CO attainment, and PO attainment traces.",
        "research": "Faculty and student publications, research grants, patents, citations, thesis tracking, and project supervision.",
        "engagement": "Institutional events, industry collaborations, MOUs, community outreach, and guest lectures.",
        "admissions": "Application intake, entrance rank verification, quota allocations, document verifications, and enrollment conversions.",
        "finance": "Student fee structures, fee payments, dues tracking, scholarships, fee waivers, and institutional ledger heads.",
        "studentlife": "Mentoring relationships, student grievances, clubs, sports achievements, and disciplinary cases.",
        "placement": "Corporate partners, job openings, placement drive registrations, student offers, internship tracking, and alumni career paths.",
        "hr": "Faculty workload allocations, performance appraisals, leave balances, professional development records, and payroll profiles.",
        "governance": "Statutory bodies (BoS, Academic Council, Governing Body), policies, meeting minutes, and compliance circulars.",
        "quality": "Internal Quality Assurance Cell (IQAC) KPI definitions, periodic measurements, accreditation metrics (NAAC/NBA/NIRF), and feedback surveys.",
        "knowledge": "Institutional documentation, policy PDF chunking, embedding vectors, and RAG knowledge extraction.",
        "agentops": "Agent registry, tool definitions, execution runs, human reviews, safety flags, and fairness monitoring.",
        "confidential": "Medical accommodations, psychological counselling notes, and crisis escalation data. Strictly isolated."
    }

    schema_classifications = {
        "core": "INTERNAL_ANALYTICS",
        "people": "INTERNAL_ANALYTICS",
        "identity": "ROLE_RESTRICTED",
        "curriculum": "INTERNAL_ANALYTICS",
        "academics": "INTERNAL_ANALYTICS",
        "attendance": "INTERNAL_ANALYTICS",
        "assessment": "INTERNAL_ANALYTICS",
        "exams": "ROLE_RESTRICTED",
        "outcomes": "INTERNAL_ANALYTICS",
        "research": "ROLE_RESTRICTED",
        "engagement": "ROLE_RESTRICTED",
        "admissions": "ROLE_RESTRICTED",
        "finance": "SENSITIVE",
        "studentlife": "SENSITIVE",
        "placement": "INTERNAL_ANALYTICS",
        "hr": "SENSITIVE",
        "governance": "ROLE_RESTRICTED",
        "quality": "INTERNAL_ANALYTICS",
        "knowledge": "ROLE_RESTRICTED",
        "agentops": "ROLE_RESTRICTED",
        "confidential": "DENY_GENERAL_ANALYTICS"
    }

    for s_name, s_comment in schema_matches:
        schemas.append({
            "schema_name": s_name,
            "description": schema_descriptions.get(s_name, s_comment.strip() if s_comment else "Institutional domain schema"),
            "classification": schema_classifications.get(s_name, "ROLE_RESTRICTED")
        })

    # 2. Views
    # Match CREATE [OR REPLACE] VIEW view_name AS ... ;
    view_pattern = re.compile(
        r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+AS\s+(.*?);(?=\s*(?:CREATE|COMMENT|SELECT|ALTER|--|\Z))',
        re.DOTALL | re.IGNORECASE
    )
    views = []
    view_names = set()
    for match in view_pattern.finditer(content):
        vname, vquery = match.groups()
        if vname in view_names:
            continue
        view_names.add(vname)
        schema_part, name_part = vname.split('.')
        # extract referenced tables
        table_refs = sorted(list(set(re.findall(r'\b([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\b', vquery))))
        table_refs = [r for r in table_refs if not r.startswith('core.add_') and not r.startswith('core.set_') and r != vname]
        
        # Determine access
        if schema_part == 'confidential':
            v_access = 'DENY_GENERAL_ANALYTICS'
        elif vname in ['attendance.v_current_attendance', 'assessment.v_course_performance', 'outcomes.v_attainment_trace', 'quality.v_kpi_latest', 'people.v_student_profile', 'academics.v_offering_roster']:
            v_access = 'ALLOW_WITH_ROLE_SCOPE'
        else:
            v_access = 'ROLE_RESTRICTED'

        views.append({
            "view_name": vname,
            "schema": schema_part,
            "name": name_part,
            "access": v_access,
            "referenced_tables": table_refs,
            "query_summary": vquery.strip().replace('\n', ' ')[:250] + "..."
        })

    # 3. RLS Tables and Policies
    rls_tables = set(re.findall(r'ALTER\s+TABLE\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY\s*;', content, re.IGNORECASE))
    
    policy_pattern = re.compile(
        r'CREATE\s+POLICY\s+([a-zA-Z0-9_]+)\s+ON\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+(?:FOR\s+([A-Z]+)\s+)?(?:TO\s+([a-zA-Z0-9_,\s]+)\s+)?USING\s*\((.*?)\)\s*;',
        re.DOTALL | re.IGNORECASE
    )
    policies = []
    for match in policy_pattern.finditer(content):
        pname, ptable, pfor, pto, pusing = match.groups()
        policies.append({
            "policy_name": pname.strip(),
            "table_name": ptable.strip(),
            "for_command": pfor.strip() if pfor else "ALL",
            "roles": pto.strip() if pto else "PUBLIC",
            "using_expression": pusing.strip().replace('\n', ' ')
        })

    # 4. Functions
    func_pattern = re.compile(
        r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s*\((.*?)\)\s*RETURNS\s+([a-zA-Z0-9_]+(?:\s+TABLE\s*\(.*?\))?)\s+AS',
        re.DOTALL | re.IGNORECASE
    )
    functions = []
    for match in func_pattern.finditer(content):
        fname, fargs, freturn = match.groups()
        functions.append({
            "function_name": fname.strip(),
            "arguments": fargs.strip().replace('\n', ' '),
            "return_type": freturn.strip()
        })

    # 5. Tables parsing
    # First find all CREATE TABLE headers
    table_headers = list(re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)', content, re.IGNORECASE))
    
    tables = []
    for i, match in enumerate(table_headers):
        tname = match.group(1).strip()
        start_pos = match.end()
        # End is either the next CREATE TABLE or EOF
        if i + 1 < len(table_headers):
            end_pos = table_headers[i + 1].start()
        else:
            end_pos = len(content)
        
        block = content[start_pos:end_pos]
        
        # Check if partitioned table
        part_match = re.search(r'PARTITION\s+OF\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+FOR\s+VALUES\s+(.*?);', block, re.IGNORECASE)
        schema_part, table_part = tname.split('.')
        
        if part_match:
            parent_table = part_match.group(1).strip()
            partition_values = part_match.group(2).strip()
            tables.append({
                "full_name": tname,
                "schema": schema_part,
                "table_name": table_part,
                "is_partition": True,
                "parent_table": parent_table,
                "partition_values": partition_values,
                "columns": [],
                "primary_key": [],
                "foreign_keys": [],
                "unique_constraints": [],
                "check_constraints": [],
                "is_rls_enabled": tname in rls_tables
            })
            continue

        # Standard table definition inside parentheses
        paren_start = block.find('(')
        if paren_start == -1:
            continue
        
        # Find matching closing parenthesis
        depth = 0
        paren_end = -1
        for idx in range(paren_start, len(block)):
            c = block[idx]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    paren_end = idx
                    break
        
        if paren_end == -1:
            continue
        
        tbody = block[paren_start + 1:paren_end]
        
        # Clean lines and split top-level commas
        clean_lines = []
        for line in tbody.splitlines():
            code_line = line.split('--')[0].strip()
            if code_line:
                clean_lines.append(code_line)
        
        combined = ' '.join(clean_lines)
        
        elements = []
        cur = []
        p_depth = 0
        for char in combined:
            if char == '(':
                p_depth += 1
            elif char == ')':
                p_depth -= 1
            if char == ',' and p_depth == 0:
                elements.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(char)
        if cur:
            elements.append(''.join(cur).strip())
        
        columns = []
        pks = []
        fks = []
        uniques = []
        checks = []

        for el in elements:
            el_upper = el.upper()
            if el_upper.startswith('PRIMARY KEY'):
                c_match = re.findall(r'\((.*?)\)', el)
                if c_match:
                    pks.extend([c.strip() for c in c_match[0].split(',')])
            elif el_upper.startswith('FOREIGN KEY'):
                fk_match = re.search(r'FOREIGN\s+KEY\s*\((.*?)\)\s*REFERENCES\s+([a-zA-Z0-9_.]+)(?:\s*\((.*?)\))?', el, re.IGNORECASE)
                if fk_match:
                    fks.append({
                        "from_columns": [c.strip() for c in fk_match.group(1).split(',')],
                        "target_table": fk_match.group(2).strip(),
                        "target_columns": [c.strip() for c in fk_match.group(3).split(',')] if fk_match.group(3) else ["id"]
                    })
            elif el_upper.startswith('UNIQUE'):
                u_match = re.findall(r'\((.*?)\)', el)
                if u_match:
                    uniques.append([c.strip() for c in u_match[0].split(',')])
            elif el_upper.startswith('CHECK'):
                chk_match = re.findall(r'CHECK\s*\((.*?)\)', el, re.IGNORECASE)
                if chk_match:
                    checks.append(chk_match[0].strip())
            else:
                # Column parsing
                parts = el.split()
                if len(parts) >= 2:
                    c_name = parts[0]
                    c_type = parts[1]
                    
                    is_pk = 'PRIMARY KEY' in el_upper
                    if is_pk:
                        pks.append(c_name)
                    is_not_null = 'NOT NULL' in el_upper or is_pk
                    
                    # inline reference
                    ref_m = re.search(r'REFERENCES\s+([a-zA-Z0-9_.]+)(?:\s*\((.*?)\))?', el, re.IGNORECASE)
                    if ref_m:
                        fks.append({
                            "from_columns": [c_name],
                            "target_table": ref_m.group(1).strip(),
                            "target_columns": [ref_m.group(2).strip()] if ref_m.group(2) else ["id"]
                        })
                    
                    # inline check
                    chk_m = re.search(r'CHECK\s*\((.*?)\)', el, re.IGNORECASE)
                    c_check = chk_m.group(1).strip() if chk_m else None

                    # inline default
                    d_m = re.search(r'DEFAULT\s+([^,]+?)(?:\s+(?:CHECK|REFERENCES|NOT|NULL|UNIQUE|PRIMARY)|\Z)', el, re.IGNORECASE)
                    c_def = d_m.group(1).strip() if d_m else None

                    columns.append({
                        "name": c_name,
                        "type": c_type,
                        "nullable": not is_not_null,
                        "is_primary_key": is_pk,
                        "default": c_def,
                        "check": c_check
                    })

        tables.append({
            "full_name": tname,
            "schema": schema_part,
            "table_name": table_part,
            "is_partition": False,
            "columns": columns,
            "primary_key": list(set(pks)),
            "foreign_keys": fks,
            "unique_constraints": uniques,
            "check_constraints": checks,
            "is_rls_enabled": tname in rls_tables
        })

    return {
        "schemas": schemas,
        "tables": tables,
        "views": views,
        "functions": functions,
        "rls_tables": sorted(list(rls_tables)),
        "policies": policies
    }

if __name__ == '__main__':
    data = parse_full_sql()
    print(f"Total Schemas: {len(data['schemas'])}")
    print(f"Total Tables: {len(data['tables'])}")
    print(f"Total Views: {len(data['views'])}")
    print(f"Total Functions: {len(data['functions'])}")
    print(f"Total RLS Tables: {len(data['rls_tables'])}")
    print(f"Total Policies: {len(data['policies'])}")
