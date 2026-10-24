"""PantheonAI PDF collector.

This module scans ``.pdf`` files, extracts text page by page, and wraps the
result in a structured :class:`DocumentObject` ready for Markdown generation
and AI indexing.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterable

try:
    from pypdf import PdfReader
except Exception as exc:  # pragma: no cover - dependency guarded at runtime
    PdfReader = None  # type: ignore[assignment]
    PYPDF_IMPORT_ERROR = exc
else:  # pragma: no cover - import sentinel for happy path
    PYPDF_IMPORT_ERROR = None

from pantheon_ai.models.document_object import DocumentObject
from pantheon_ai.utils.sha_cache import ShaCache


class PdfCollector:
    """Collect ``.pdf`` files from a folder tree."""

    CACHE_NAMESPACE = "pdf"

    def __init__(self, input_folder: str | Path, cache_file: str | Path | None = None):
        self.input_folder = Path(input_folder)
        if not self.input_folder.exists():
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")
        if not self.input_folder.is_dir():
            raise NotADirectoryError(f"Input folder is not a directory: {self.input_folder}")
        self.cache_file = Path(cache_file) if cache_file is not None else None

    def scan(self) -> list[Path]:
        """Return all supported PDF files under the input folder."""

        return sorted(
            path
            for path in self.input_folder.rglob("*.pdf")
            if path.is_file()
        )

    def read_file(self, file_path: Path) -> DocumentObject:
        """Read and extract a single PDF file."""

        raw = file_path.read_bytes()
        reader = self._open_reader(file_path)
        text = self._extract_text(reader)
        relative = file_path.relative_to(self.input_folder)
        page_count = len(reader.pages)

        return DocumentObject(
            source_type="PDF",
            title=file_path.stem,
            name=file_path.stem,
            filename=file_path.name,
            relative_path=str(relative.parent),
            absolute_path=str(file_path),
            text=text,
            encoding="binary/pdf",
            size=len(raw),
            page_count=page_count,
            sha256=sha256(raw).hexdigest(),
            metadata={
                "pages": page_count,
                "encrypted": getattr(reader, "is_encrypted", False),
                "extensions": [".pdf"],
            },
        )

    def collect(self, changed_only: bool = False) -> list[DocumentObject]:
        """Collect all supported PDF documents."""

        documents: list[DocumentObject] = []
        cache = ShaCache(self.cache_file) if self.cache_file is not None else None
        current_keys: list[str] = []

        for file_path in self.scan():
            try:
                document = self.read_file(file_path)
                cache_key = self._cache_key(file_path)
                current_keys.append(cache_key)

                if cache is not None:
                    previous_sha = cache.get(self.CACHE_NAMESPACE, cache_key)
                    if changed_only and previous_sha == document.sha256:
                        continue
                    cache.set(self.CACHE_NAMESPACE, cache_key, document.sha256)

                documents.append(document)
            except Exception as exc:  # pragma: no cover - collector must continue
                print(f"[ERROR] {file_path}: {exc}")

        if cache is not None:
            cache.prune(self.CACHE_NAMESPACE, current_keys)
            cache.save()

        return documents

    def collect_iter(self, changed_only: bool = False) -> Iterable[DocumentObject]:
        """Yield PDF documents one by one."""

        for document in self.collect(changed_only=changed_only):
            yield document

    def _open_reader(self, file_path: Path):
        if PdfReader is None:
            raise ImportError(
                "pypdf is required for PDF support. Install it with 'pip install pypdf'."
            ) from PYPDF_IMPORT_ERROR

        reader = PdfReader(str(file_path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                pass
        return reader

    def _extract_text(self, reader) -> str:
        parts: list[str] = []

        for index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            page_text = self._normalize(page_text)
            if page_text:
                parts.append(f"[Page {index}]\n{page_text}")

        return self._normalize("\n\n".join(parts))

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.replace("\r\n", "\n").replace("\r", "\n").split())

    def _cache_key(self, file_path: Path) -> str:
        relative = file_path.relative_to(self.input_folder)
        return relative.as_posix()


if __name__ == "__main__":
    collector = PdfCollector(Path("input") / "docs")
    docs = collector.collect()

    print(f"Found {len(docs)} PDF files")
    for doc in docs:
        print(f"- {doc.relative_path}/{doc.filename} ({doc.size} bytes, {doc.page_count} pages)")
