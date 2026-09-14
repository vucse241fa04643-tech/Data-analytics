"""
Agent 63 – Approved Student Field Catalog & Security Classifications
Defines the authoritative approved catalog of student-record attributes,
safe SQL column projection mappings, and strictly prohibited/restricted fields.

Zero raw column pass-through. Zero SELECT * permitted.
"""

from typing import Any, Dict, List, Set

# Authoritative mapping of approved student attributes to safe SQL column projections
# using the standard table aliases:
# s: people.student
# p: people.person
# b: curriculum.batch
# pr: curriculum.programme
# d: core.department
# sec: curriculum.section
APPROVED_STUDENT_FIELDS: Dict[str, Dict[str, Any]] = {
    "student_id": {
        "sql_expr": "s.student_id",
        "alias": "student_id",
        "type": "uuid",
        "display_name": "Student ID",
        "category": "IDENTIFIER",
        "sensitive": False,
    },
    "roll_no": {
        "sql_expr": "s.roll_no",
        "alias": "roll_no",
        "type": "string",
        "display_name": "Roll Number",
        "category": "IDENTIFIER",
        "sensitive": False,
    },
    "register_no": {
        "sql_expr": "s.register_no",
        "alias": "register_no",
        "type": "string",
        "display_name": "University Register Number",
        "category": "IDENTIFIER",
        "sensitive": False,
    },
    "admission_no": {
        "sql_expr": "s.admission_no",
        "alias": "admission_no",
        "type": "string",
        "display_name": "Admission Number",
        "category": "IDENTIFIER",
        "sensitive": False,
    },
    "full_name": {
        "sql_expr": "p.full_name",
        "alias": "full_name",
        "type": "string",
        "display_name": "Full Name",
        "category": "BIOGRAPHICAL",
        "sensitive": False,
    },
    "gender": {
        "sql_expr": "p.gender",
        "alias": "gender",
        "type": "string",
        "display_name": "Gender",
        "category": "BIOGRAPHICAL",
        "sensitive": False,
    },
    "primary_email": {
        "sql_expr": "p.primary_email",
        "alias": "primary_email",
        "type": "string",
        "display_name": "Institutional Email",
        "category": "CONTACT",
        "sensitive": False,
    },
    "department_code": {
        "sql_expr": "d.code",
        "alias": "department_code",
        "type": "string",
        "display_name": "Department Code",
        "category": "ACADEMIC_ORGANIZATION",
        "sensitive": False,
    },
    "department_name": {
        "sql_expr": "d.name",
        "alias": "department_name",
        "type": "string",
        "display_name": "Department Name",
        "category": "ACADEMIC_ORGANIZATION",
        "sensitive": False,
    },
    "programme_code": {
        "sql_expr": "pr.code",
        "alias": "programme_code",
        "type": "string",
        "display_name": "Programme Code",
        "category": "ACADEMIC_ORGANIZATION",
        "sensitive": False,
    },
    "programme_name": {
        "sql_expr": "pr.name",
        "alias": "programme_name",
        "type": "string",
        "display_name": "Programme Name",
        "category": "ACADEMIC_ORGANIZATION",
        "sensitive": False,
    },
    "batch_label": {
        "sql_expr": "b.label",
        "alias": "batch_label",
        "type": "string",
        "display_name": "Batch",
        "category": "ACADEMIC_PROGRESSION",
        "sensitive": False,
    },
    "section_code": {
        "sql_expr": "sec.code",
        "alias": "section_code",
        "type": "string",
        "display_name": "Section",
        "category": "ACADEMIC_PROGRESSION",
        "sensitive": False,
    },
    "current_year_of_study": {
        "sql_expr": "s.current_year_of_study",
        "alias": "current_year_of_study",
        "type": "integer",
        "display_name": "Year of Study",
        "category": "ACADEMIC_PROGRESSION",
        "sensitive": False,
    },
    "status": {
        "sql_expr": "s.status",
        "alias": "status",
        "type": "string",
        "display_name": "Status",
        "category": "ACADEMIC_PROGRESSION",
        "sensitive": False,
    },
}

# Standard default fields projected if user does not request specific fields
DEFAULT_STUDENT_PROJECTION: List[str] = [
    "roll_no",
    "full_name",
    "department_code",
    "batch_label",
    "section_code",
    "current_year_of_study",
    "status",
]

# Prohibited / restricted fields that must NEVER be returned in general student listings
STRICTLY_PROHIBITED_FIELDS: Set[str] = {
    # Identity credentials and secrets
    "password",
    "password_hash",
    "credential",
    "auth_token",
    "token",
    "salt",
    "secret",
    # Sensitive personal information
    "social_category",
    "caste",
    "religion",
    "blood_group",
    "aadhaar",
    "national_id",
    "passport",
    "address",
    "address_line1",
    "address_line2",
    "city",
    "pincode",
    "pin_code",
    "guardian_income",
    "annual_income",
    "fee_arrears",
    "fee_outstanding",
    # Sensitive confidential & psychological records
    "counselling",
    "counselling_notes",
    "psychological_record",
    "medical_record",
    "disability",
    "disciplinary",
    "disciplinary_record",
    "malpractice",
    "incident_notes",
    # Exam questions and answers
    "question_paper",
    "answer_key",
    "raw_marks",
}

# Supported filter keys for student retrieval
ALLOWED_STUDENT_FILTER_KEYS: Set[str] = {
    "department",
    "department_code",
    "department_id",
    "programme",
    "programme_code",
    "programme_id",
    "batch",
    "batch_id",
    "batch_label",
    "section",
    "section_id",
    "section_code",
    "year_of_study",
    "current_year_of_study",
    "roll_no",
    "student_id",
    "status",
}
