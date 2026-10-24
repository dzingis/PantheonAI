"""PantheonAI document markdown generator.

This module converts extracted Word and PDF documents into Markdown files that
can be indexed by AnythingLLM or other downstream AI tooling.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from pantheon_ai.models.document_object import DocumentObject


class DocumentMarkdownGenerator:
    """Generate Markdown documents from extracted source documents."""

    def __init__(self, output_folder: str | Path):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        document: DocumentObject,
        relative_path: str | Path | None = None,
    ) -> Path:
        """Generate a Markdown file for one document."""

        target_dir = self.output_folder
        if relative_path:
            target_dir = target_dir / Path(relative_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        output_path = target_dir / self._build_file_name(document)
        output_path.write_text(self.build_markdown(document), encoding="utf-8")
        return output_path

    def build_markdown(self, document: DocumentObject) -> str:
        """Build Markdown content without writing it to disk."""

        lines: list[str] = []

        lines.append(f"# {self._title(document)}")
        lines.append("")
        lines.append("## Source")
        lines.append("")
        lines.append(f"- Original file: {document.absolute_path or 'Unknown'}")
        lines.append(f"- Original name: {document.filename or document.document_name or 'Unknown'}")
        lines.append(f"- Source type: {document.source_name}")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- Source Type: {document.source_name}")
        lines.append(f"- Title: {document.document_name}")
        lines.append(f"- File Name: {document.filename}")
        lines.append(f"- Relative Path: {document.relative_path or '.'}")
        lines.append(f"- Absolute Path: {document.absolute_path}")
        lines.append(f"- Size: {document.size} bytes")
        lines.append(f"- Page Count: {document.page_count}")
        lines.append(f"- SHA256: {document.sha256}")
        lines.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")

        if document.metadata:
            lines.append("## Extra Metadata")
            lines.append("")
            for key, value in document.metadata.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        lines.append("## Extracted Text")
        lines.append("")
        lines.append("```text")
        lines.append(document.text.strip() or "No extractable text found.")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def preview(self, document: DocumentObject) -> str:
        """Return the Markdown content without saving it."""

        return self.build_markdown(document)

    def _build_file_name(self, document: DocumentObject) -> str:
        base = document.name or document.filename or "unknown_document"
        safe = re.sub(r"[^A-Za-z0-9_\-\.]+", "_", base).strip("._")
        if not safe:
            safe = "unknown_document"
        return f"{safe}.md"

    @staticmethod
    def _title(document: DocumentObject) -> str:
        if document.document_name:
            return f"{document.source_name}: {document.document_name}"
        return document.source_name or "Document"


if __name__ == "__main__":
    sample = DocumentObject(
        source_type="Word",
        title="Sample",
        name="Sample",
        filename="Sample.docx",
        relative_path="docs",
        absolute_path=r"C:\Temp\Sample.docx",
        text="This is a sample document.",
        size=1234,
        metadata={"paragraphs": 2},
    )

    generator = DocumentMarkdownGenerator(Path("knowledge") / "docs")
    print(generator.preview(sample))
