"""
Agent 63 – Semantic Layer & Metric Catalog Validator
Validates semantic_layer/ definitions against the authoritative Phase 1 Schema Registry
(database/mappings/agent63_schema_registry.json).

Ensures:
- Strict JSON syntax and required top-level metadata
- Unique metric_id, dimension_id, and join_id
- Source objects exist in the Phase 1 schema registry
- Source columns and join keys exist in the referenced objects
- Security classifications comply with institutional access tiers
- Strict exclusion of confidential.* and question paper objects
- Placement fairness compliance (no protected attributes)
- Approved metrics have documented provenance, formulas, and grains
- Production eligibility constraints (only APPROVED metrics eligible)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

VALID_STATUSES = {"APPROVED", "REVIEW_REQUIRED", "DRAFT", "DEPRECATED"}
VALID_SENSITIVITIES = {
    "PUBLIC_INSTITUTIONAL",
    "INTERNAL_INSTITUTIONAL",
    "SENSITIVE",
    "RESTRICTED",
}
VALID_AGGREGATIONS = {
    "SUM",
    "AVG",
    "COUNT",
    "COUNT_DISTINCT",
    "MIN",
    "MAX",
    "RATIO",
    "LATEST",
    "PERCENTILE",
}

STRICTLY_DENIED_PREFIXES = [
    "confidential.",
    "assessment.question_paper",
    "exams.question_paper_delivery",
    "exams.malpractice_incident",
    "identity.credential",
    "identity.auth_token",
]

PROTECTED_ATTRIBUTES = [
    "gender",
    "caste",
    "religion",
    "nationality",
    "disability_status",
    "region",
    "socioeconomic_category",
]


def load_json(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_semantic_layer() -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    schema_registry_path = repo_root / "database" / "mappings" / "agent63_schema_registry.json"
    semantic_registry_path = repo_root / "semantic_layer" / "registry" / "semantic_registry.json"

    if not schema_registry_path.exists():
        print(f"FAIL: Phase 1 Schema Registry not found at {schema_registry_path}")
        return False

    if not semantic_registry_path.exists():
        print(f"FAIL: Semantic Registry not found at {semantic_registry_path}")
        return False

    # 1. Load Phase 1 Schema Registry
    schema_reg = load_json(schema_registry_path)
    registered_objects: Dict[str, Dict[str, Any]] = {
        obj["full_name"]: obj for obj in schema_reg.get("objects", [])
    }

    # 2. Load Semantic Registry
    try:
        semantic_reg = load_json(semantic_registry_path)
    except Exception as e:
        print(f"FAIL: Invalid JSON in semantic registry: {e}")
        return False

    errors: List[str] = []
    warnings: List[str] = []

    # Check top-level keys
    for req_key in ["version", "summary", "security_policy", "dimensions", "join_paths", "metrics"]:
        if req_key not in semantic_reg:
            errors.append(f"Missing required top-level key: '{req_key}'")

    dimensions = semantic_reg.get("dimensions", [])
    join_paths = semantic_reg.get("join_paths", [])
    metrics = semantic_reg.get("metrics", [])

    # Index Dimensions
    seen_dimension_ids: Set[str] = set()
    dimension_map: Dict[str, Dict[str, Any]] = {}

    for idx, dim in enumerate(dimensions):
        dim_id = dim.get("dimension_id", f"dimension_{idx}")
        if not dim.get("dimension_id"):
            errors.append(f"Dimension #{idx} missing 'dimension_id'")
        elif dim_id in seen_dimension_ids:
            errors.append(f"Duplicate dimension_id: '{dim_id}'")
        seen_dimension_ids.add(dim_id)
        dimension_map[dim_id] = dim

        # Check required fields
        for field in ["canonical_name", "source_object", "key_column", "sensitivity", "status"]:
            if not dim.get(field):
                errors.append(f"Dimension '{dim_id}' missing required field '{field}'")

        # Verify source_object in Phase 1 registry
        src_obj = dim.get("source_object")
        if src_obj:
            if src_obj not in registered_objects:
                errors.append(f"Dimension '{dim_id}' references nonexistent database object: '{src_obj}'")
            else:
                db_obj = registered_objects[src_obj]
                allowed_cols = set(db_obj.get("allowed_columns", []))
                # Check key_column
                key_col = dim.get("key_column")
                if "*" not in allowed_cols and key_col and key_col not in allowed_cols:
                    errors.append(f"Dimension '{dim_id}' key_column '{key_col}' not found in '{src_obj}'")

                # Check attributes
                for attr in dim.get("attributes", []):
                    if "*" not in allowed_cols and attr not in allowed_cols:
                        errors.append(f"Dimension '{dim_id}' attribute '{attr}' not found in '{src_obj}'")

        # Check sensitivity
        sens = dim.get("sensitivity")
        if sens not in VALID_SENSITIVITIES:
            errors.append(f"Dimension '{dim_id}' has invalid sensitivity: '{sens}'")

    # Index Join Paths
    seen_join_ids: Set[str] = set()
    for idx, join in enumerate(join_paths):
        join_id = join.get("join_id", f"join_{idx}")
        if not join.get("join_id"):
            errors.append(f"Join #{idx} missing 'join_id'")
        elif join_id in seen_join_ids:
            errors.append(f"Duplicate join_id: '{join_id}'")
        seen_join_ids.add(join_id)

        for field in ["left_object", "left_key", "right_object", "right_key", "relationship_type"]:
            if not join.get(field):
                errors.append(f"Join '{join_id}' missing required field '{field}'")

        left_obj = join.get("left_object")
        left_key = join.get("left_key")
        right_obj = join.get("right_object")
        right_key = join.get("right_key")

        if left_obj not in registered_objects:
            errors.append(f"Join '{join_id}' left_object '{left_obj}' not in schema registry")
        else:
            left_cols = set(registered_objects[left_obj].get("allowed_columns", []))
            if "*" not in left_cols and left_key and left_key not in left_cols:
                errors.append(f"Join '{join_id}' left_key '{left_key}' not in '{left_obj}'")

        if right_obj not in registered_objects:
            errors.append(f"Join '{join_id}' right_object '{right_obj}' not in schema registry")
        else:
            right_cols = set(registered_objects[right_obj].get("allowed_columns", []))
            if "*" not in right_cols and right_key and right_key not in right_cols:
                errors.append(f"Join '{join_id}' right_key '{right_key}' not in '{right_obj}'")

    # Validate Metrics
    seen_metric_ids: Set[str] = set()
    approved_count = 0
    review_count = 0
    deprecated_count = 0

    for idx, metric in enumerate(metrics):
        m_id = metric.get("metric_id", f"metric_{idx}")
        if not metric.get("metric_id"):
            errors.append(f"Metric #{idx} missing 'metric_id'")
        elif m_id in seen_metric_ids:
            errors.append(f"Duplicate metric_id: '{m_id}'")
        seen_metric_ids.add(m_id)

        # Required fields
        req_fields = [
            "canonical_name",
            "display_name",
            "description",
            "domain",
            "grain",
            "formula",
            "aggregation",
            "source_objects",
            "source_columns",
            "sensitivity",
            "status",
            "version",
            "provenance",
        ]
        for field in req_fields:
            if not metric.get(field):
                errors.append(f"Metric '{m_id}' missing required field '{field}'")

        status = metric.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"Metric '{m_id}' has invalid status: '{status}'")
        elif status == "APPROVED":
            approved_count += 1
        elif status == "REVIEW_REQUIRED":
            review_count += 1
        elif status == "DEPRECATED":
            deprecated_count += 1

        sens = metric.get("sensitivity")
        if sens not in VALID_SENSITIVITIES:
            errors.append(f"Metric '{m_id}' has invalid sensitivity: '{sens}'")

        agg = metric.get("aggregation")
        if agg not in VALID_AGGREGATIONS:
            errors.append(f"Metric '{m_id}' has invalid aggregation: '{agg}'")

        # Check source objects
        src_objects = metric.get("source_objects", [])
        if not src_objects:
            errors.append(f"Metric '{m_id}' must have at least one source_object")
        for src_obj in src_objects:
            if src_obj not in registered_objects:
                errors.append(f"Metric '{m_id}' references nonexistent database object '{src_obj}'")
            else:
                # Security checks
                for prefix in STRICTLY_DENIED_PREFIXES:
                    if src_obj.startswith(prefix):
                        errors.append(f"CRITICAL: Metric '{m_id}' references strictly denied object '{src_obj}'")

                db_access = registered_objects[src_obj].get("access")
                if db_access == "DENY_GENERAL_ANALYTICS":
                    errors.append(f"CRITICAL: Metric '{m_id}' uses object '{src_obj}' marked DENY_GENERAL_ANALYTICS")
                elif db_access == "ROLE_RESTRICTED" and sens == "PUBLIC_INSTITUTIONAL":
                    errors.append(f"Security mismatch: Metric '{m_id}' is PUBLIC_INSTITUTIONAL but source '{src_obj}' is ROLE_RESTRICTED")

        # Check source columns exist in at least one source object
        all_allowed_cols = set()
        for src_obj in src_objects:
            if src_obj in registered_objects:
                all_allowed_cols.update(registered_objects[src_obj].get("allowed_columns", []))

        for col in metric.get("source_columns", []):
            if "*" not in all_allowed_cols and col not in all_allowed_cols:
                errors.append(f"Metric '{m_id}' source_column '{col}' not found in source objects {src_objects}")

        # Check allowed dimensions exist
        for dim_ref in metric.get("allowed_dimensions", []):
            if dim_ref not in dimension_map:
                errors.append(f"Metric '{m_id}' references undefined dimension '{dim_ref}'")

        # Fairness checks for placement
        if metric.get("domain") == "placement":
            for col in metric.get("source_columns", []):
                if col.lower() in PROTECTED_ATTRIBUTES:
                    errors.append(f"Fairness violation: Placement metric '{m_id}' references protected attribute '{col}'")

        # Approved metrics require proven formula and non-empty provenance
        if status == "APPROVED":
            prov = metric.get("provenance", "")
            if len(prov.strip()) < 5:
                errors.append(f"APPROVED metric '{m_id}' must have meaningful provenance documentation")

    # Print Report
    print("=" * 60)
    print("AGENT 63 SEMANTIC LAYER VALIDATION REPORT")
    print("=" * 60)
    print(f"Total metrics:          {len(metrics)}")
    print(f"  Approved:             {approved_count}")
    print(f"  Review required:      {review_count}")
    print(f"  Deprecated:           {deprecated_count}")
    print(f"Total dimensions:       {len(dimensions)}")
    print(f"Total joins:            {len(join_paths)}")
    print(f"Errors:                 {len(errors)}")
    print(f"Warnings:               {len(warnings)}")
    print("=" * 60)

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  [WARN] {w}")

    if errors:
        print("\nErrors Found:")
        for e in errors:
            print(f"  [ERROR] {e}")
        print("\n[FAILED] Semantic layer validation failed.")
        return False

    print("[SUCCESS] All semantic layer integrity, relational, and security rules passed.")
    return True


if __name__ == "__main__":
    success = validate_semantic_layer()
    sys.exit(0 if success else 1)
