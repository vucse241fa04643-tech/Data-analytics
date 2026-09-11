"""
Agent 63 – Schema Registry Service
Safely loads, validates, and provides in-memory read-only access to the authoritative
Phase 1 Schema Registry (database/mappings/agent63_schema_registry.json).

CRITICAL ARCHITECTURAL CONSTRAINTS:
- Phase 1 registry is the sole source of truth for database object mappings.
- Never hard-code college tables/schemas into backend code.
- Never expose raw registry internals through a public API endpoint in Phase 2.
- The service acts strictly as an internal backend metadata provider for future query services.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.errors import SchemaRegistryError
from backend.app.core.logging import get_logger

logger = get_logger("agent63.services.schema_registry")


class SchemaRegistryService:
    """Singleton service providing verified access to the Phase 1 Schema Registry."""

    def __init__(self, registry_path: Optional[str] = None):
        self._custom_path = registry_path
        self._registry_data: Optional[Dict[str, Any]] = None
        self._indexed_objects: Dict[str, Dict[str, Any]] = {}
        self._is_valid: bool = False
        self._resolved_path: Optional[Path] = None

    def _locate_registry_file(self) -> Path:
        """Determines the authoritative path to agent63_schema_registry.json."""
        if self._custom_path:
            p = Path(self._custom_path)
            if p.is_file():
                return p
            raise SchemaRegistryError(
                message=f"Specified schema registry path does not exist: {self._custom_path}"
            )

        if settings.SCHEMA_REGISTRY_PATH:
            p = Path(settings.SCHEMA_REGISTRY_PATH)
            if p.is_file():
                return p

        # Search relative to this file: backend/app/services -> repo root
        candidates = [
            Path(__file__).resolve().parents[3] / "database" / "mappings" / "agent63_schema_registry.json",
            Path.cwd() / "database" / "mappings" / "agent63_schema_registry.json",
            Path.cwd().parent / "database" / "mappings" / "agent63_schema_registry.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate

        raise SchemaRegistryError(
            message="Authoritative Phase 1 Schema Registry file not found. Ensure 'database/mappings/agent63_schema_registry.json' exists."
        )

    def load(self, force_reload: bool = False) -> Dict[str, Any]:
        """Loads and validates the schema registry structure, indexing objects by full_name."""
        if self._registry_data is not None and not force_reload:
            return self._registry_data

        path = self._locate_registry_file()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read or parse schema registry from {path}: {str(e)}")
            raise SchemaRegistryError(
                message=f"Schema registry JSON could not be parsed: {str(e)}"
            )

        self._validate_structure(data, path)
        
        # Build fast in-memory index by full_name
        indexed = {}
        for obj in data.get("objects", []):
            full_name = obj.get("full_name") or f"{obj.get('schema')}.{obj.get('object')}"
            indexed[full_name] = obj

        self._indexed_objects = indexed
        self._registry_data = data
        self._resolved_path = path
        self._is_valid = True

        total_objects = len(self._indexed_objects)
        logger.info(
            f"Schema registry successfully loaded from {path.name}: {total_objects} objects verified."
        )
        return self._registry_data

    def _validate_structure(self, data: Any, path: Path) -> None:
        """Lightweight runtime verification of essential Phase 1 registry attributes."""
        if not isinstance(data, dict):
            raise SchemaRegistryError(message="Schema registry root must be a JSON object.")

        required_keys = {"version", "database_engine", "objects"}
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise SchemaRegistryError(
                message=f"Schema registry missing mandatory top-level keys: {missing_keys}"
            )

        objects = data.get("objects")
        if not isinstance(objects, list):
            raise SchemaRegistryError(message="Schema registry 'objects' must be a list of object definitions.")

        if len(objects) == 0:
            raise SchemaRegistryError(message="Schema registry contains 0 objects.")

        # Sample check first 10 objects for required Phase 1 schema attributes
        for obj in objects[:10]:
            if not isinstance(obj, dict):
                raise SchemaRegistryError(message="Object entry in schema registry is not a valid JSON dictionary.")
            if "schema" not in obj or "object" not in obj or "object_type" not in obj or "access" not in obj:
                raise SchemaRegistryError(
                    message=f"Object entry '{obj.get('full_name', 'unknown')}' is missing schema, object, object_type, or access."
                )

    @property
    def is_ready(self) -> bool:
        """Returns True if the registry has been successfully loaded and validated."""
        if self._registry_data is None:
            try:
                self.load()
                return self._is_valid
            except Exception:
                return False
        return self._is_valid

    def get_object_count(self) -> int:
        """Returns the total number of registered database objects."""
        if not self.is_ready:
            return 0
        return len(self._indexed_objects)

    def get_object(self, qualified_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves schema metadata for a qualified object name (e.g., 'people.student' or 'core.institution').
        Returns None if not found or if registry is unavailable.
        """
        if not self.is_ready:
            return None
        return self._indexed_objects.get(qualified_name)

    def get_schemas(self) -> List[str]:
        """Returns unique list of schema names present in the registry."""
        if not self.is_ready:
            return []
        schemas = {
            obj.get("schema") for obj in self._indexed_objects.values() if obj.get("schema")
        }
        return sorted(list(schemas))

    def get_summary(self) -> Dict[str, Any]:
        """Returns safe summary metrics of the loaded schema registry."""
        if not self.is_ready or not self._registry_data:
            return {"status": "unavailable"}
        return {
            "version": self._registry_data.get("version"),
            "database_engine": self._registry_data.get("database_engine"),
            "total_objects": len(self._indexed_objects),
            "schemas_count": len(self.get_schemas()),
            "access_summary": self._registry_data.get("access_summary", {}),
        }


# Global service instance
schema_registry_service = SchemaRegistryService()
