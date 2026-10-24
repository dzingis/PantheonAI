"""PantheonAI SQL markdown generator.

This module converts parsed SQL metadata into Markdown documents that are
friendly for downstream indexing and retrieval.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable
import re

from pantheon_ai.analyzers.sql_parser import SqlObject


class MarkdownGenerator:
    """Generate Markdown documents from parsed SQL objects."""

    def __init__(self, output_folder: str | Path):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        sql_object: SqlObject,
        relative_path: str | Path | None = None,
        source_path: str | Path | None = None,
    ) -> Path:
        """Generate a Markdown file for one SQL object.

        Parameters
        ----------
        sql_object:
            Parsed SQL object.
        relative_path:
            Optional relative path inside the knowledge folder. When omitted,
            the file is written directly into the generator output folder.
        source_path:
            Optional original source file path. When provided, the generated
            Markdown includes a Source section that points back to the SQL file.
        """

        target_dir = self.output_folder
        if relative_path:
            target_dir = target_dir / Path(relative_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        file_name = self._build_file_name(sql_object)
        output_path = target_dir / file_name
        output_path.write_text(
            self.build_markdown(sql_object, source_path=source_path),
            encoding="utf-8",
        )
        return output_path

    def generate_many(
        self,
        sql_objects: Iterable[SqlObject],
        relative_path: str | Path | None = None,
        source_path: str | Path | None = None,
    ) -> list[Path]:
        """Generate Markdown files for many SQL objects."""

        return [
            self.generate(sql_object, relative_path=relative_path, source_path=source_path)
            for sql_object in sql_objects
        ]

    def build_markdown(self, sql_object: SqlObject, source_path: str | Path | None = None) -> str:
        """Build Markdown content without writing it to disk."""

        lines: list[str] = []

        lines.append(f"# {self._title(sql_object)}")
        lines.append("")
        lines.append("## Source")
        lines.append("")
        if source_path:
            source = Path(source_path)
            lines.append(f"- Original file: {source}")
            lines.append(f"- Original name: {source.name}")
        else:
            lines.append("- Original file: Unknown")
            lines.append(f"- Original name: {sql_object.name or 'Unknown'}")
        lines.append(f"- Source type: SQL")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- Type: {sql_object.object_type}")
        lines.append(f"- Schema: {sql_object.schema}")
        lines.append(f"- Name: {sql_object.name}")
        lines.append(f"- Object Name: {sql_object.object_name}")
        lines.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")

        lines.append("## Parameters")
        lines.append("")
        if sql_object.parameters:
            lines.extend(f"- {item}" for item in sql_object.parameters)
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append("## Tables")
        lines.append("")
        if sql_object.tables:
            lines.extend(f"- {item}" for item in sql_object.tables)
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append("## EXEC Calls")
        lines.append("")
        if sql_object.execs:
            lines.extend(f"- {item}" for item in sql_object.execs)
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append("## Variables")
        lines.append("")
        if sql_object.variables:
            lines.extend(f"- {item}" for item in sql_object.variables)
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append("## Temp Tables")
        lines.append("")
        if sql_object.temp_tables:
            lines.extend(f"- {item}" for item in sql_object.temp_tables)
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append("## CTEs")
        lines.append("")
        if sql_object.ctes:
            lines.extend(f"- {item}" for item in sql_object.ctes)
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append("## Original SQL")
        lines.append("")
        lines.append("```sql")
        lines.append(sql_object.sql.strip())
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def preview(self, sql_object: SqlObject, source_path: str | Path | None = None) -> str:
        """Return Markdown content without saving it."""

        return self.build_markdown(sql_object, source_path=source_path)

    def _build_file_name(self, sql_object: SqlObject) -> str:
        base = sql_object.name or "unknown_sql_object"
        safe = re.sub(r"[^A-Za-z0-9_\-\.]+", "_", base).strip("._")
        if not safe:
            safe = "unknown_sql_object"
        return f"{safe}.md"

    @staticmethod
    def _title(sql_object: SqlObject) -> str:
        if sql_object.object_name:
            return f"{sql_object.object_type}: {sql_object.object_name}"
        if sql_object.name:
            return f"{sql_object.object_type}: {sql_object.name}"
        return sql_object.object_type or "SQL Object"


if __name__ == "__main__":
    sample = SqlObject(
        object_type="Procedure",
        schema="dbo",
        name="pHE_Test",
        sql="""
CREATE OR ALTER PROCEDURE dbo.pHE_Test
    @anMoveQid INT,
    @acDept VARCHAR(20)
AS
BEGIN
    SELECT *
    FROM tHE_Move
    EXEC dbo.pHE_DoSomething
END
""",
        parameters=["@anMoveQid", "@acDept"],
        tables=["tHE_Move"],
        execs=["dbo.pHE_DoSomething"],
    )

    generator = MarkdownGenerator(Path("knowledge") / "sql")
    print(generator.preview(sample, source_path=r"D:\Projects\PantheonAI\input\sql\pHE_Test.sql"))
