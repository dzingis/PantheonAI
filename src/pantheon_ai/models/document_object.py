"""PantheonAI document model.

This module defines a structured representation for extracted Word and PDF
content so it can be transformed into Markdown and indexed by AI tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DocumentObject:
    """Structured representation of one source document."""

    source_type: str = "Document"
    title: str = ""
    name: str = ""
    filename: str = ""
    relative_path: str = ""
    absolute_path: str = ""
    text: str = ""
    encoding: str = "utf-8"
    size: int = 0
    page_count: int = 0
    sha256: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def document_name(self) -> str:
        """Return a display name for the document."""

        return self.title or self.name or self.filename or ""

    @property
    def source_name(self) -> str:
        """Return a source label suitable for logging and markdown headers."""

        return self.source_type or "Document"
