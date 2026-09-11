"""
Agent 63 – Test Schema Registry Service
Validates integration with Phase 1 schema registry without modifying original files.
"""

import pytest
from backend.app.core.errors import SchemaRegistryError
from backend.app.services.schema_registry import SchemaRegistryService


def test_schema_registry_loads_phase1_registry():
    """Verify Phase 1 registry loads all 236 registered database objects."""
    service = SchemaRegistryService()
    data = service.load()
    assert data["version"] == "1.0"
    assert data["database_engine"] == "postgresql"
    assert service.get_object_count() == 236
    assert service.is_ready is True


def test_schema_registry_lookups():
    """Verify in-memory object lookups return accurate metadata."""
    service = SchemaRegistryService()
    service.load()

    # Known Phase 1 table
    inst = service.get_object("core.institution")
    assert inst is not None
    assert inst["schema"] == "core"
    assert inst["object"] == "institution"
    assert inst["object_type"] == "table"
    assert inst["access"] == "ALLOW"
    assert "institution_id" in inst["allowed_columns"]

    # Non-existent table
    missing = service.get_object("nonexistent.table")
    assert missing is None


def test_schema_registry_schemas_list():
    """Verify registered schema list contains expected 21 institutional schemas."""
    service = SchemaRegistryService()
    service.load()
    schemas = service.get_schemas()
    assert len(schemas) == 21
    assert "core" in schemas
    assert "academics" in schemas
    assert "finance" in schemas
    assert "confidential" in schemas


def test_schema_registry_missing_file(tmp_path):
    """Verify SchemaRegistryError is raised when registry file does not exist."""
    non_existent = tmp_path / "non_existent_registry.json"
    service = SchemaRegistryService(registry_path=str(non_existent))
    with pytest.raises(SchemaRegistryError) as exc_info:
        service.load()
    assert "does not exist" in str(exc_info.value.message).lower()


def test_schema_registry_malformed_json(tmp_path):
    """Verify SchemaRegistryError is raised when registry contains invalid JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ broken json", encoding="utf-8")
    service = SchemaRegistryService(registry_path=str(bad_file))
    with pytest.raises(SchemaRegistryError):
        service.load()
