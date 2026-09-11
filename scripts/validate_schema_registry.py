"""
Schema Registry Validator for Agent 63
Validates database/mappings/agent63_schema_registry.json against strict integrity,
classification, and security rules.
"""

import json
import os
import sys

VALID_ACCESS_LEVELS = {
    "ALLOW",
    "ALLOW_WITH_ROLE_SCOPE",
    "ROLE_RESTRICTED",
    "RESTRICTED",
    "DENY_GENERAL_ANALYTICS"
}

VALID_SENSITIVITY_TIERS = {
    "PUBLIC_ANALYTICS",
    "INTERNAL_ANALYTICS",
    "ROLE_RESTRICTED",
    "SENSITIVE",
    "HIGHLY_SENSITIVE"
}

KNOWN_SCHEMAS = {
    "core", "people", "identity", "curriculum", "academics",
    "attendance", "assessment", "exams", "outcomes", "research",
    "engagement", "admissions", "finance", "studentlife", "placement",
    "hr", "governance", "quality", "knowledge", "agentops", "confidential"
}

STRICTLY_DENIED_PREFIXES = [
    "confidential.",
    "assessment.question_paper",
    "exams.question_paper_delivery",
    "exams.malpractice_incident"
]

CREDENTIAL_PATTERNS = [
    "password", "secret", "token", "private_key", "jwt_secret", "postgres://"
]

def validate_registry():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    registry_path = os.path.join(root_dir, "database", "mappings", "agent63_schema_registry.json")

    if not os.path.exists(registry_path):
        print(f"FAIL: Registry file not found at {registry_path}")
        return False

    with open(registry_path, "r", encoding="utf-8") as f:
        try:
            registry = json.load(f)
        except json.JSONDecodeError as e:
            print(f"FAIL: Invalid JSON in registry: {e}")
            return False

    errors = []
    warnings = []

    # Check top-level metadata
    required_top = ["version", "database_engine", "database_version_target", "objects"]
    for req in required_top:
        if req not in registry:
            errors.append(f"Missing required top-level key: '{req}'")

    if registry.get("database_engine") != "postgresql":
        errors.append(f"Invalid database_engine: expected 'postgresql', got '{registry.get('database_engine')}'")

    objects = registry.get("objects", [])
    if not isinstance(objects, list) or len(objects) == 0:
        errors.append("Registry must contain a non-empty list of 'objects'")

    seen_objects = set()

    for idx, obj in enumerate(objects):
        obj_id = f"Object #{idx}"
        # Check required object keys
        req_keys = ["schema", "object", "full_name", "object_type", "access", "sensitivity", "purpose", "grain"]
        for rk in req_keys:
            if rk not in obj:
                errors.append(f"{obj_id}: Missing required key '{rk}'")

        full_name = obj.get("full_name", "")
        obj_id = f"Object '{full_name}'"

        # Check duplicate
        if full_name in seen_objects:
            errors.append(f"{obj_id}: Duplicate object definition in registry")
        seen_objects.add(full_name)

        # Check schema validity
        schema = obj.get("schema")
        if schema not in KNOWN_SCHEMAS:
            errors.append(f"{obj_id}: Unknown schema '{schema}'")

        # Check access level
        access = obj.get("access")
        if access not in VALID_ACCESS_LEVELS:
            errors.append(f"{obj_id}: Invalid access level '{access}'")

        # Check sensitivity tier
        sensitivity = obj.get("sensitivity")
        if sensitivity not in VALID_SENSITIVITY_TIERS:
            errors.append(f"{obj_id}: Invalid sensitivity tier '{sensitivity}'")

        # CRITICAL SECURITY CHECK: Strictly denied items must NOT be allowed
        for denied_prefix in STRICTLY_DENIED_PREFIXES:
            if full_name.startswith(denied_prefix) and access != "DENY_GENERAL_ANALYTICS":
                errors.append(f"SECURITY VIOLATION: '{full_name}' must have access 'DENY_GENERAL_ANALYTICS', got '{access}'")

        # Check for leaked credentials or secrets in text fields
        serialized_obj = json.dumps(obj).lower()
        for pat in CREDENTIAL_PATTERNS:
            if f'"{pat}"' in serialized_obj or f"'{pat}'" in serialized_obj:
                # Flag if it looks like actual credential value
                if "password123" in serialized_obj or "secret_key" in serialized_obj:
                    errors.append(f"SECURITY VIOLATION: Possible real secret pattern '{pat}' in {obj_id}")

        # Check allowed columns vs restricted columns
        allowed = obj.get("allowed_columns", [])
        restricted = obj.get("restricted_columns", [])
        overlap = set(allowed).intersection(set(restricted))
        if overlap:
            errors.append(f"{obj_id}: Overlap between allowed and restricted columns: {overlap}")

    print("=" * 60)
    print(f"AGENT 63 SCHEMA REGISTRY VALIDATION REPORT")
    print(f"Total Objects Validated: {len(objects)}")
    print(f"Errors Found: {len(errors)}")
    print(f"Warnings Found: {len(warnings)}")
    print("=" * 60)

    if errors:
        for err in errors:
            print(f"[ERROR] {err}")
        return False
    else:
        print("[SUCCESS] All schema registry integrity and security rules passed.")
        return True

if __name__ == "__main__":
    success = validate_registry()
    sys.exit(0 if success else 1)
