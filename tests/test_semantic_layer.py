"""
Agent 63 – Semantic Layer Security & Integrity Tests
Validates that the Semantic Layer adheres to strict security, schema compliance,
and institutional governance standards.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_REG_PATH = REPO_ROOT / "database" / "mappings" / "agent63_schema_registry.json"
SEMANTIC_REG_PATH = REPO_ROOT / "semantic_layer" / "registry" / "semantic_registry.json"


@pytest.fixture(scope="module")
def schema_registry():
    with open(SCHEMA_REG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def semantic_registry():
    with open(SEMANTIC_REG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestSemanticLayerIntegrity:
    def test_01_semantic_registry_exists_and_valid_json(self, semantic_registry):
        assert "version" in semantic_registry
        assert "metrics" in semantic_registry
        assert "dimensions" in semantic_registry
        assert "join_paths" in semantic_registry
        assert "security_policy" in semantic_registry
        assert len(semantic_registry["metrics"]) >= 20

    def test_02_all_metrics_have_unique_ids(self, semantic_registry):
        ids = [m["metric_id"] for m in semantic_registry["metrics"]]
        assert len(ids) == len(set(ids)), f"Duplicate metric IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_03_all_dimensions_have_unique_ids(self, semantic_registry):
        ids = [d["dimension_id"] for d in semantic_registry["dimensions"]]
        assert len(ids) == len(set(ids)), f"Duplicate dimension IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_04_all_joins_have_unique_ids(self, semantic_registry):
        ids = [j["join_id"] for j in semantic_registry["join_paths"]]
        assert len(ids) == len(set(ids)), f"Duplicate join IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_05_all_source_objects_exist_in_phase1_registry(self, semantic_registry, schema_registry):
        registered = {o["full_name"] for o in schema_registry["objects"]}
        for metric in semantic_registry["metrics"]:
            for src_obj in metric["source_objects"]:
                assert src_obj in registered, f"Metric {metric['metric_id']} references unmapped table {src_obj}"
        for dim in semantic_registry["dimensions"]:
            assert dim["source_object"] in registered, f"Dimension {dim['dimension_id']} references unmapped table {dim['source_object']}"


class TestSemanticSecurity:
    def test_06_confidential_schema_strictly_excluded(self, semantic_registry):
        for metric in semantic_registry["metrics"]:
            for src in metric["source_objects"]:
                assert not src.startswith("confidential."), f"Metric {metric['metric_id']} violates confidential exclusion: {src}"
        for dim in semantic_registry["dimensions"]:
            assert not dim["source_object"].startswith("confidential."), f"Dimension {dim['dimension_id']} violates confidential exclusion: {dim['source_object']}"

    def test_07_question_paper_and_sensitive_exam_objects_excluded(self, semantic_registry):
        forbidden = ["assessment.question_paper", "exams.question_paper_delivery", "exams.malpractice_incident"]
        for metric in semantic_registry["metrics"]:
            for src in metric["source_objects"]:
                assert src not in forbidden, f"Metric {metric['metric_id']} references sensitive exam object {src}"

    def test_08_placement_fairness_no_protected_attributes(self, semantic_registry):
        protected = {"gender", "caste", "religion", "nationality", "region"}
        placement_metrics = [m for m in semantic_registry["metrics"] if m.get("domain") == "placement"]
        for m in placement_metrics:
            for col in m.get("source_columns", []):
                assert col.lower() not in protected, f"Placement metric {m['metric_id']} references protected attribute {col}"

    def test_09_approved_metrics_have_provenance_and_valid_status(self, semantic_registry):
        for metric in semantic_registry["metrics"]:
            assert metric["status"] in {"APPROVED", "REVIEW_REQUIRED", "DRAFT", "DEPRECATED"}
            if metric["status"] == "APPROVED":
                assert len(metric.get("provenance", "").strip()) >= 5, f"Approved metric {metric['metric_id']} lacks provenance"

    def test_10_no_restricted_objects_marked_public(self, semantic_registry, schema_registry):
        db_map = {o["full_name"]: o for o in schema_registry["objects"]}
        for metric in semantic_registry["metrics"]:
            if metric.get("sensitivity") == "PUBLIC_INSTITUTIONAL":
                for src in metric["source_objects"]:
                    assert db_map[src].get("access") != "ROLE_RESTRICTED", f"Public metric {metric['metric_id']} relies on ROLE_RESTRICTED {src}"
