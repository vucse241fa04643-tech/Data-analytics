"""Agent 63 - Phase 14: Export Artifact Store
In-memory, bounded, thread-safe LRU store with TTL for caching server-side analytical artifacts.

SECURITY INVARIANTS:
- Bounded memory footprint (MAX_ENTRIES = 1000).
- Strict TTL expiration (default 15 minutes / 900s).
- Thread-safe mutations using threading.RLock().
- Eliminates client-supplied result injection.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.schemas.export import ExportArtifact

logger = get_logger("agent63.services.export_artifact_store")


class ExportArtifactStore:
    """Thread-safe bounded in-memory store for analytical export artifacts."""

    def __init__(
        self,
        max_entries: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ):
        self._max_entries = max_entries or settings.EXPORT_ARTIFACT_MAX_ENTRIES
        self._ttl_seconds = ttl_seconds or settings.EXPORT_ARTIFACT_TTL_SECONDS
        self._store: OrderedDict[str, ExportArtifact] = OrderedDict()
        self._lock = threading.RLock()

    def save_artifact(self, artifact: ExportArtifact) -> None:
        """Saves or updates an artifact with bounded LRU eviction."""
        if not settings.EXPORT_ENABLED:
            return

        now = datetime.now(timezone.utc)
        artifact.expires_at = now + timedelta(seconds=self._ttl_seconds)
        with self._lock:
            # Evict expired head items
            while self._store and next(iter(self._store.values())).expires_at < now:
                self._store.popitem(last=False)

            # Enforce max capacity limit (LRU eviction)
            while len(self._store) >= self._max_entries:
                self._store.popitem(last=False)

            self._store[artifact.request_id] = artifact
            self._store.move_to_end(artifact.request_id)

        logger.debug(f"ExportArtifact saved: request_id={artifact.request_id} metric={artifact.metric_id}")

    def get_artifact(self, request_id: str) -> Optional[ExportArtifact]:
        """Retrieves an artifact by request_id if present and not expired."""
        now = datetime.now(timezone.utc)
        with self._lock:
            artifact = self._store.get(request_id)
            if artifact is None:
                return None
            if artifact.expires_at < now:
                del self._store[request_id]
                logger.debug(f"ExportArtifact expired and removed: request_id={request_id}")
                return None
            return artifact

    def clear_expired(self) -> int:
        """Removes all expired entries and returns the count removed."""
        now = datetime.now(timezone.utc)
        removed = 0
        with self._lock:
            expired_keys = [k for k, v in self._store.items() if v.expires_at < now]
            for k in expired_keys:
                del self._store[k]
                removed += 1
        return removed

    def clear_all(self) -> None:
        """Clears all artifacts (useful for isolated unit tests)."""
        with self._lock:
            self._store.clear()

    def clear(self) -> None:
        """Alias for clear_all."""
        self.clear_all()

    def count(self) -> int:
        """Returns the number of active artifacts currently in the store."""
        with self._lock:
            return len(self._store)

    def size(self) -> int:
        """Alias for count."""
        return self.count()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_singleton_export_store: Optional[ExportArtifactStore] = None


def get_export_artifact_store() -> ExportArtifactStore:
    """Dependency provider for ExportArtifactStore."""
    global _singleton_export_store
    if _singleton_export_store is None:
        _singleton_export_store = ExportArtifactStore()
    return _singleton_export_store


def reset_export_artifact_store() -> None:
    """Resets singleton instance for test isolation."""
    global _singleton_export_store
    if _singleton_export_store is not None:
        _singleton_export_store.clear_all()
    _singleton_export_store = None
