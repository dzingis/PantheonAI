"""PantheonAI SQL collector.

This module scans an input folder recursively, finds ``.sql`` files,
reads their contents, and returns structured documents that can later be
parsed and transformed into knowledge documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import hashlib


@dataclass(slots=True)
class SqlDocument:
    """Represents a single SQL file collected from disk."""

    name: str
    filename: str
    relative_path: str
    absolute_path: str
    sql: str
    encoding: str = "utf-8"
    sha256: str = ""
    size: int = 0


class SqlCollector:
    """Collects SQL files from a folder tree."""

    def __init__(self, input_folder: str | Path):
        self.input_folder = Path(input_folder)
        if not self.input_folder.exists():
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")
        if not self.input_folder.is_dir():
            raise NotADirectoryError(f"Input folder is not a directory: {self.input_folder}")

    def scan(self) -> List[Path]:
        """Return all ``.sql`` files under ``input_folder`` recursively."""
        return sorted(
            path
            for path in self.input_folder.rglob("*.sql")
            if path.is_file()
        )

    def read_file(self, file_path: Path) -> SqlDocument:
        """Read one SQL file and return a structured document."""
        raw = file_path.read_bytes()
        encoding = self._detect_encoding(raw)
        sql = raw.decode(encoding, errors="replace")

        relative = file_path.relative_to(self.input_folder)
        sha256 = hashlib.sha256(raw).hexdigest()

        return SqlDocument(
            name=file_path.stem,
            filename=file_path.name,
            relative_path=str(relative.parent),
            absolute_path=str(file_path),
            sql=sql,
            encoding=encoding,
            sha256=sha256,
            size=len(raw),
        )

    def collect(self) -> List[SqlDocument]:
        """Collect all SQL documents from disk."""
        documents: List[SqlDocument] = []
        for file_path in self.scan():
            try:
                documents.append(self.read_file(file_path))
            except Exception as exc:  # pragma: no cover - collector should continue
                print(f"[ERROR] {file_path}: {exc}")
        return documents

    def collect_iter(self) -> Iterable[SqlDocument]:
        """Yield documents one by one."""
        for file_path in self.scan():
            try:
                yield self.read_file(file_path)
            except Exception as exc:  # pragma: no cover - collector should continue
                print(f"[ERROR] {file_path}: {exc}")

    @staticmethod
    def _detect_encoding(raw: bytes) -> str:
        """Detect a usable encoding for SQL text.

        The collector prefers UTF-8, then tries UTF-8 with BOM, UTF-16,
        and finally falls back to cp1250 which is common for Croatian SQL
        source files on Windows.
        """

        candidates = ("utf-8", "utf-8-sig", "utf-16", "cp1250", "latin-1")
        for encoding in candidates:
            try:
                raw.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        return "utf-8"


if __name__ == "__main__":
    collector = SqlCollector(Path("input") / "sql")
    docs = collector.collect()

    print(f"Found {len(docs)} SQL files")
    for doc in docs:
        print(f"- {doc.relative_path}/{doc.filename} ({doc.size} bytes, {doc.encoding})")
