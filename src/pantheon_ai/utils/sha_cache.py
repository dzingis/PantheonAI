"""PantheonAI SHA cache helpers.

This module stores per-source file hashes so collectors can skip files that
have not changed since the last build.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Iterable


@dataclass(slots=True)
class CacheEntry:
    """One cached file hash entry."""

    sha256: str
    updated_at: str


class ShaCache:
    """Simple JSON-backed SHA cache for incremental builds."""

    def __init__(self, cache_file: str | Path):
        self.cache_file = Path(cache_file)
        self._data: dict[str, dict[str, dict[str, str]]] = {
            "version": 1,
            "files": {},
        }
        self._dirty = False
        self.load()

    def load(self) -> None:
        """Load cache data from disk if the file exists."""

        if not self.cache_file.exists():
            return

        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return

        if not isinstance(payload, dict):
            return

        version = payload.get("version", 1)
        files = payload.get("files", {})
        if not isinstance(files, dict):
            files = {}

        normalized_files: dict[str, dict[str, str]] = {}
        for key, value in files.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            sha = value.get("sha256", "")
            updated_at = value.get("updated_at", "")
            if isinstance(sha, str) and isinstance(updated_at, str):
                normalized_files[key] = {
                    "sha256": sha,
                    "updated_at": updated_at,
                }

        self._data = {
            "version": int(version) if isinstance(version, int) else 1,
            "files": normalized_files,
        }
        self._dirty = False

    def get(self, namespace: str, key: str) -> str | None:
        """Return the cached SHA for a file if present."""

        entry = self._data["files"].get(self._make_key(namespace, key))
        if not entry:
            return None
        sha = entry.get("sha256")
        return sha if isinstance(sha, str) and sha else None

    def set(self, namespace: str, key: str, sha256: str) -> None:
        """Store or update a file SHA in the cache."""

        cache_key = self._make_key(namespace, key)
        self._data["files"][cache_key] = {
            "sha256": sha256,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._dirty = True

    def prune(self, namespace: str, active_keys: Iterable[str]) -> int:
        """Remove stale keys for one namespace and return the number removed."""

        active = {self._make_key(namespace, key) for key in active_keys}
        prefix = f"{namespace}::"

        removed = 0
        new_files: dict[str, dict[str, str]] = {}
        for cache_key, entry in self._data["files"].items():
            if cache_key.startswith(prefix) and cache_key not in active:
                removed += 1
                self._dirty = True
                continue
            new_files[cache_key] = entry

        self._data["files"] = new_files
        return removed

    def save(self) -> None:
        """Persist the cache to disk."""

        if not self._dirty and self.cache_file.exists():
            return

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._dirty = False

    @staticmethod
    def _make_key(namespace: str, key: str) -> str:
        normalized = key.replace("\\", "/").strip("/")
        return f"{namespace}::{normalized}"
