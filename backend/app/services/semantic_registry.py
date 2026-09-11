"""
Agent 63 – Semantic Registry Service
Provides safe, in-memory, read-only access to the authoritative Phase 4 Semantic Registry
(semantic_layer/registry/semantic_registry.json).

CRITICAL ARCHITECTURAL CONSTRAINTS:
- Semantic Layer defines institutional metric formulas and dimensions; LLMs must never invent formulas.
- Never connects to PostgreSQL directly.
- Never executes SQL.
- Never calls an external LLM.
- Exposes verified semantic metadata strictly for internal backend query construction services.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.errors import SemanticRegistryError
from backend.app.core.logging import get_logger

logger = get_logger("agent63.services.semantic_registry")


class SemanticRegistryService:
    """Singleton service providing verified access to the Phase 4 Semantic Registry."""

    def __init__(self, registry_path: Optional[str] = None):
        self._custom_path = registry_path
        self._registry_data: Optional[Dict[str, Any]] = None
        self._metrics_by_id: Dict[str, Dict[str, Any]] = {}
        self._metrics_by_domain: Dict[str, List[Dict[str, Any]]] = {}
        self._approved_metrics: List[Dict[str, Any]] = []
        self._dimensions_by_id: Dict[str, Dict[str, Any]] = {}
        self._join_paths: List[Dict[str, Any]] = []
        self._is_valid: bool = False
        self._resolved_path: Optional[Path] = None

    def _locate_registry_file(self) -> Path:
        """Determines the authoritative path to semantic_registry.json."""
        if self._custom_path:
            p = Path(self._custom_path)
            if p.is_file():
                return p
            raise SemanticRegistryError(
                message=f"Specified semantic registry path does not exist: {self._custom_path}"
            )

        if settings.SEMANTIC_REGISTRY_PATH:
            p = Path(settings.SEMANTIC_REGISTRY_PATH)
            if p.is_file():
                return p

        # Search relative to this file: backend/app/services -> repo root
        candidates = [
            Path(__file__).resolve().parents[3] / "semantic_layer" / "registry" / "semantic_registry.json",
            Path.cwd() / "semantic_layer" / "registry" / "semantic_registry.json",
            Path.cwd().parent / "semantic_layer" / "registry" / "semantic_registry.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate

        raise SemanticRegistryError(
            message="Authoritative Phase 4 Semantic Registry file not found. Ensure 'semantic_layer/registry/semantic_registry.json' exists."
        )

    def load(self, force_reload: bool = False) -> Dict[str, Any]:
        """Loads, parses, and indexes the semantic registry."""
        if self._registry_data is not None and not force_reload:
            return self._registry_data

        path = self._locate_registry_file()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to parse semantic registry JSON at {path}: {e}")
            raise SemanticRegistryError(
                message=f"Semantic registry JSON parsing failed: {e}",
                details={"path": str(path)},
            )

        # Validate required root keys
        required_keys = ["version", "dimensions", "join_paths", "metrics"]
        for k in required_keys:
            if k not in data:
                raise SemanticRegistryError(
                    message=f"Malformed semantic registry: missing top-level key '{k}'",
                    details={"missing_key": k},
                )

        # Clear and index
        self._metrics_by_id = {}
        self._metrics_by_domain = {}
        self._approved_metrics = []
        self._dimensions_by_id = {}
        self._join_paths = data.get("join_paths", [])

        # Index dimensions
        for dim in data.get("dimensions", []):
            dim_id = dim.get("dimension_id")
            if dim_id:
                self._dimensions_by_id[dim_id] = dim

        # Index metrics
        for metric in data.get("metrics", []):
            m_id = metric.get("metric_id")
            if not m_id:
                continue
            self._metrics_by_id[m_id] = metric

            domain = metric.get("domain", "uncategorized")
            if domain not in self._metrics_by_domain:
                self._metrics_by_domain[domain] = []
            self._metrics_by_domain[domain].append(metric)

            if metric.get("status") == "APPROVED":
                self._approved_metrics.append(metric)

        self._registry_data = data
        self._resolved_path = path
        self._is_valid = True

        logger.info(
            f"Semantic registry successfully loaded from {path.name}: "
            f"{len(self._metrics_by_id)} metrics ({len(self._approved_metrics)} approved), "
            f"{len(self._dimensions_by_id)} dimensions, {len(self._join_paths)} join paths verified."
        )
        return self._registry_data

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    def get_metric(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific metric definition by metric_id."""
        if not self._is_valid:
            self.load()
        return self._metrics_by_id.get(metric_id)

    def get_metrics_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Retrieves all metrics belonging to a specific institutional domain."""
        if not self._is_valid:
            self.load()
        return self._metrics_by_domain.get(domain, [])

    def get_approved_metrics(self) -> List[Dict[str, Any]]:
        """Retrieves only APPROVED metrics eligible for production query planning."""
        if not self._is_valid:
            self.load()
        return list(self._approved_metrics)

    def get_dimension(self, dimension_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a dimension definition by dimension_id."""
        if not self._is_valid:
            self.load()
        return self._dimensions_by_id.get(dimension_id)

    def get_dimensions(self) -> List[Dict[str, Any]]:
        """Retrieves all defined dimensions."""
        if not self._is_valid:
            self.load()
        return list(self._dimensions_by_id.values())

    def get_join_paths(
        self, left_object: Optional[str] = None, right_object: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves join paths optionally filtered by left and/or right objects."""
        if not self._is_valid:
            self.load()
        results = self._join_paths
        if left_object:
            results = [j for j in results if j.get("left_object") == left_object]
        if right_object:
            results = [j for j in results if j.get("right_object") == right_object]
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Provides high-level summary of semantic objects."""
        if not self._is_valid:
            self.load()
        return {
            "version": self._registry_data.get("version", "1.0"),
            "total_metrics": len(self._metrics_by_id),
            "approved_metrics": len(self._approved_metrics),
            "review_required_metrics": sum(
                1 for m in self._metrics_by_id.values() if m.get("status") == "REVIEW_REQUIRED"
            ),
            "total_dimensions": len(self._dimensions_by_id),
            "total_joins": len(self._join_paths),
            "domains": list(self._metrics_by_domain.keys()),
        }


# Singleton instance pattern
_semantic_registry_service: Optional[SemanticRegistryService] = None


def get_semantic_registry_service() -> SemanticRegistryService:
    global _semantic_registry_service
    if _semantic_registry_service is None:
        _semantic_registry_service = SemanticRegistryService()
        _semantic_registry_service.load()
    return _semantic_registry_service
