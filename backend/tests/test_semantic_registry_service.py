"""
Agent 63 – Backend Semantic Registry Service Tests
Verifies the in-memory loading, indexing, and querying behavior of SemanticRegistryService.
"""

from pathlib import Path
import pytest

from backend.app.core.errors import SemanticRegistryError
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)


def test_semantic_registry_service_loads_successfully():
    service = SemanticRegistryService()
    data = service.load()
    assert service.is_valid
    assert "metrics" in data
    assert len(service.get_dimensions()) == 10
    assert len(service.get_join_paths()) == 24


def test_get_metric_by_id():
    service = get_semantic_registry_service()
    metric = service.get_metric("attendance.percentage")
    assert metric is not None
    assert metric["canonical_name"] == "attendance_percentage"
    assert metric["status"] == "APPROVED"
    assert metric["domain"] == "attendance"

    non_existent = service.get_metric("invalid.non_existent_metric")
    assert non_existent is None


def test_get_metrics_by_domain():
    service = get_semantic_registry_service()
    att_metrics = service.get_metrics_by_domain("attendance")
    assert len(att_metrics) == 6
    for m in att_metrics:
        assert m["domain"] == "attendance"

    empty_domain = service.get_metrics_by_domain("non_existent_domain")
    assert empty_domain == []


def test_get_approved_metrics_excludes_review_required():
    service = get_semantic_registry_service()
    approved = service.get_approved_metrics()
    assert len(approved) == 24
    for m in approved:
        assert m["status"] == "APPROVED"

    # Verify review required metric is not in approved list
    approved_ids = {m["metric_id"] for m in approved}
    assert "attendance.students_below_threshold" not in approved_ids
    assert "placement.placement_rate" not in approved_ids


def test_get_dimensions_and_single_dimension():
    service = get_semantic_registry_service()
    dims = service.get_dimensions()
    assert len(dims) == 10

    dept = service.get_dimension("dim.department")
    assert dept is not None
    assert dept["source_object"] == "core.department"
    assert dept["key_column"] == "department_id"


def test_get_join_paths_filtering():
    service = get_semantic_registry_service()
    all_joins = service.get_join_paths()
    assert len(all_joins) == 24

    filtered = service.get_join_paths(left_object="core.department")
    assert len(filtered) >= 2
    for j in filtered:
        assert j["left_object"] == "core.department"


def test_semantic_registry_service_summary():
    service = get_semantic_registry_service()
    summary = service.get_summary()
    assert summary["total_metrics"] == 26
    assert summary["approved_metrics"] == 24
    assert summary["review_required_metrics"] == 2
    assert summary["total_dimensions"] == 10
    assert summary["total_joins"] == 24
    assert "attendance" in summary["domains"]
    assert "assessment" in summary["domains"]


def test_semantic_registry_missing_file_raises_error():
    service = SemanticRegistryService(registry_path="non_existent/path/registry.json")
    with pytest.raises(SemanticRegistryError):
        service.load()
