"""PantheonAI SQL parser.

This module turns raw SQL text into structured metadata that can be
used by downstream generators and knowledge builders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence
import re

try:
    from pantheon_ai.collectors.sql_collector import SqlDocument
except Exception:  # pragma: no cover - import fallback for direct execution
    SqlDocument = None  # type: ignore[assignment]


@dataclass(slots=True)
class SqlObject:
    """Structured representation of a SQL object."""

    object_type: str = "Unknown"
    schema: str = "dbo"
    name: str = ""
    sql: str = ""
    parameters: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    execs: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    temp_tables: list[str] = field(default_factory=list)
    ctes: list[str] = field(default_factory=list)

    @property
    def object_name(self) -> str:
        """Return the fully qualified object name when available."""
        if self.schema and self.name:
            return f"{self.schema}.{self.name}"
        return self.name or ""


class SqlParser:
    """Parse SQL scripts into structured metadata."""

    _TYPE_PATTERNS: tuple[tuple[str, str], ...] = (
        (r"\bCREATE\s+OR\s+ALTER\s+PROCEDURE\b", "Procedure"),
        (r"\bCREATE\s+PROCEDURE\b", "Procedure"),
        (r"\bALTER\s+PROCEDURE\b", "Procedure"),
        (r"\bCREATE\s+OR\s+ALTER\s+PROC\b", "Procedure"),
        (r"\bCREATE\s+PROC\b", "Procedure"),
        (r"\bALTER\s+PROC\b", "Procedure"),
        (r"\bCREATE\s+OR\s+ALTER\s+VIEW\b", "View"),
        (r"\bCREATE\s+VIEW\b", "View"),
        (r"\bALTER\s+VIEW\b", "View"),
        (r"\bCREATE\s+OR\s+ALTER\s+FUNCTION\b", "Function"),
        (r"\bCREATE\s+FUNCTION\b", "Function"),
        (r"\bALTER\s+FUNCTION\b", "Function"),
        (r"\bCREATE\s+OR\s+ALTER\s+TRIGGER\b", "Trigger"),
        (r"\bCREATE\s+TRIGGER\b", "Trigger"),
        (r"\bALTER\s+TRIGGER\b", "Trigger"),
    )

    _OBJECT_KEYWORDS: tuple[str, ...] = ("PROCEDURE", "PROC", "VIEW", "FUNCTION", "TRIGGER")

    def parse(self, source: str | Path | SqlDocument) -> SqlObject:
        """Parse SQL text or a :class:`SqlDocument` into ``SqlObject``."""

        sql = self._read_source(source)
        cleaned = self.normalize(sql)

        sql_object = SqlObject(sql=cleaned)
        sql_object.object_type = self.detect_type(cleaned)
        sql_object.schema, sql_object.name = self.detect_name(cleaned)
        sql_object.parameters = self.extract_parameters(cleaned)
        sql_object.tables = self.extract_tables(cleaned)
        sql_object.execs = self.extract_execs(cleaned)
        sql_object.variables = self.extract_variables(cleaned)
        sql_object.temp_tables = self.extract_temp_tables(cleaned)
        sql_object.ctes = self.extract_ctes(cleaned)
        return sql_object

    def normalize(self, sql: str | None) -> str:
        """Normalize line endings and trim outer whitespace."""

        if not sql:
            return ""

        sql = sql.replace("\r\n", "\n")
        sql = sql.replace("\r", "\n")
        return sql.strip()

    def detect_type(self, sql: str) -> str:
        """Detect SQL object type from the declaration header."""

        header = self._header(sql)
        for pattern, object_type in self._TYPE_PATTERNS:
            if re.search(pattern, header, re.IGNORECASE):
                return object_type
        return "Unknown"

    def detect_name(self, sql: str) -> tuple[str, str]:
        """Detect schema and object name."""

        header = self._header(sql)
        patterns = (
            r"\b(?:CREATE\s+OR\s+ALTER\s+|CREATE\s+|ALTER\s+)?(?:PROCEDURE|PROC|VIEW|FUNCTION|TRIGGER)\s+((?:\[[^\]]+\]|[A-Za-z0-9_#]+)(?:\s*\.\s*(?:\[[^\]]+\]|[A-Za-z0-9_#]+))?)",
        )

        for pattern in patterns:
            match = re.search(pattern, header, re.IGNORECASE)
            if not match:
                continue

            qualified = match.group(1)
            parts = [self._clean_identifier(part) for part in re.split(r"\s*\.\s*", qualified)]
            parts = [part for part in parts if part]
            if len(parts) >= 2:
                return parts[-2], parts[-1]
            if parts:
                return "dbo", parts[-1]

        return "dbo", ""

    def extract_parameters(self, sql: str) -> list[str]:
        """Extract parameters from the declaration header and local scope."""

        header = self._declaration_segment(sql)
        parameters = self._ordered_unique(r"@[A-Za-z_][A-Za-z0-9_@$#]*", header)
        return parameters

    def extract_tables(self, sql: str) -> list[str]:
        """Extract referenced table-like identifiers."""

        body = self._body(sql)
        patterns = (
            r"\bFROM\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
            r"\bJOIN\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
            r"\bUPDATE\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
            r"\bINTO\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
            r"\bMERGE\s+INTO\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
            r"\bDELETE\s+FROM\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
            r"\bTRUNCATE\s+TABLE\s+((?:\[[^\]]+\]|[#A-Za-z0-9_@$]+)(?:\s*\.\s*(?:\[[^\]]+\]|[#A-Za-z0-9_@$]+))*)",
        )

        tables: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, body, re.IGNORECASE):
                identifier = self._clean_qualified_identifier(match.group(1))
                if identifier and identifier.upper() != "SELECT" and identifier not in tables:
                    tables.append(identifier)
        return tables

    def extract_execs(self, sql: str) -> list[str]:
        """Extract EXEC / EXECUTE targets."""

        body = self._body(sql)
        execs: list[str] = []
        pattern = r"\bEXEC(?:UTE)?\s+(?:@?\w+\s*=\s*)?((?:\[[^\]]+\]|[A-Za-z0-9_@$#]+)(?:\s*\.\s*(?:\[[^\]]+\]|[A-Za-z0-9_@$#]+))*)"
        for match in re.finditer(pattern, body, re.IGNORECASE):
            proc = self._clean_qualified_identifier(match.group(1))
            if not proc or proc.startswith("@"):  # dynamic SQL or variable assignment
                continue
            if proc.upper() in {"SP_EXECUTESQL", "EXEC", "EXECUTE"}:
                continue
            if proc not in execs:
                execs.append(proc)
        return execs

    def extract_variables(self, sql: str) -> list[str]:
        """Extract local variables and parameters from the script body."""

        body = self._body(sql)
        variables = self._ordered_unique(r"@[A-Za-z_][A-Za-z0-9_@$#]*", body)
        return variables

    def extract_temp_tables(self, sql: str) -> list[str]:
        """Extract temp tables (``#`` and ``##`` variants)."""

        body = self._body(sql)
        patterns = (
            r"\bCREATE\s+TABLE\s+(##?[A-Za-z0-9_]+)",
            r"\bINTO\s+(##?[A-Za-z0-9_]+)",
            r"\bFROM\s+(##?[A-Za-z0-9_]+)",
            r"\bJOIN\s+(##?[A-Za-z0-9_]+)",
            r"\bUPDATE\s+(##?[A-Za-z0-9_]+)",
            r"\bDELETE\s+FROM\s+(##?[A-Za-z0-9_]+)",
        )

        temp_tables: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, body, re.IGNORECASE):
                temp_table = match.group(1)
                if temp_table not in temp_tables:
                    temp_tables.append(temp_table)
        return temp_tables

    def extract_ctes(self, sql: str) -> list[str]:
        """Extract common table expression names."""

        body = self._body(sql)
        ctes: list[str] = []

        for match in re.finditer(r"\bWITH\s+([A-Za-z_][A-Za-z0-9_@$#]*)\s+AS\b", body, re.IGNORECASE):
            name = match.group(1)
            if name not in ctes:
                ctes.append(name)

        return ctes

    def summary(self, sql_object: SqlObject) -> dict[str, int | str]:
        """Return a compact summary for logging and tests."""

        return {
            "Type": sql_object.object_type,
            "Schema": sql_object.schema,
            "Name": sql_object.name,
            "Parameters": len(sql_object.parameters),
            "Tables": len(sql_object.tables),
            "Execs": len(sql_object.execs),
            "Variables": len(sql_object.variables),
            "TempTables": len(sql_object.temp_tables),
            "CTEs": len(sql_object.ctes),
        }

    def _read_source(self, source: str | Path | SqlDocument) -> str:
        """Read SQL text from supported sources."""

        if SqlDocument is not None and isinstance(source, SqlDocument):
            return source.sql
        if isinstance(source, Path):
            return source.read_text(encoding="utf-8", errors="replace")
        if hasattr(source, "sql"):
            return str(getattr(source, "sql"))
        return str(source)

    def _header(self, sql: str) -> str:
        """Return the declaration header portion of the SQL text."""

        cleaned = self._strip_comments(self.normalize(sql))
        cut_points = [
            self._find_keyword(cleaned, r"\bAS\b"),
            self._find_keyword(cleaned, r"\bRETURNS\b"),
        ]
        cut_points = [point for point in cut_points if point != -1]
        if not cut_points:
            return cleaned[:1000]
        return cleaned[: min(cut_points)]

    def _declaration_segment(self, sql: str) -> str:
        """Return the declaration segment where parameters usually live."""

        cleaned = self._strip_comments(self.normalize(sql))
        start = self._find_signature_start(cleaned)
        if start == -1:
            return cleaned[:1000]
        end = self._find_keyword(cleaned[start:], r"\bAS\b")
        if end == -1:
            return cleaned[start:]
        return cleaned[start : start + end]

    def _body(self, sql: str) -> str:
        """Return the body portion of the SQL script with comments removed."""

        cleaned = self._strip_comments(self.normalize(sql))
        start = self._find_keyword(cleaned, r"\bAS\b")
        if start == -1:
            return cleaned
        return cleaned[start:]

    def _find_signature_start(self, sql: str) -> int:
        """Find the start of the object declaration."""

        patterns = (
            r"\bCREATE\s+OR\s+ALTER\s+(?:PROCEDURE|PROC|VIEW|FUNCTION|TRIGGER)\b",
            r"\bCREATE\s+(?:PROCEDURE|PROC|VIEW|FUNCTION|TRIGGER)\b",
            r"\bALTER\s+(?:PROCEDURE|PROC|VIEW|FUNCTION|TRIGGER)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                return match.start()
        return -1

    @staticmethod
    def _strip_comments(sql: str) -> str:
        """Remove SQL line and block comments."""

        sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
        sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
        return sql

    @staticmethod
    def _find_keyword(sql: str, pattern: str) -> int:
        """Return the start position of a regex keyword or ``-1``."""

        match = re.search(pattern, sql, re.IGNORECASE)
        return match.start() if match else -1

    @staticmethod
    def _ordered_unique(pattern: str, text: str) -> list[str]:
        """Return unique regex matches in order of appearance."""

        items: list[str] = []
        for match in re.finditer(pattern, text):
            value = match.group(0)
            if value not in items:
                items.append(value)
        return items

    @staticmethod
    def _clean_identifier(identifier: str) -> str:
        """Clean a single SQL identifier segment."""

        identifier = identifier.strip()
        if identifier.startswith("[") and identifier.endswith("]"):
            identifier = identifier[1:-1]
        return identifier.strip()

    def _clean_qualified_identifier(self, identifier: str) -> str:
        """Normalize a possibly qualified SQL identifier."""

        parts = [self._clean_identifier(part) for part in re.split(r"\s*\.\s*", identifier)]
        parts = [part for part in parts if part]
        return ".".join(parts)


if __name__ == "__main__":
    sample = """
    CREATE OR ALTER PROCEDURE dbo.pHE_Test
        @anMoveQid INT,
        @acDept VARCHAR(20)
    AS
    BEGIN
        DECLARE @nValue INT;

        WITH Sales AS (
            SELECT *
            FROM tHE_Move
        )

        SELECT *
        INTO #TmpMove
        FROM Sales;

        UPDATE tHE_MoveItem
        SET acStatus = 'X';

        INSERT INTO tHE_Document (acKey)
        SELECT acKey
        FROM tHE_Move;

        EXEC pHE_InsertMove;
        EXEC dbo.pHE_UpdateMove;
    END
    """

    parser = SqlParser()
    result = parser.parse(sample)

    print(parser.summary(result))
    print("Parameters:", result.parameters)
    print("Tables:", result.tables)
    print("Execs:", result.execs)
    print("Variables:", result.variables)
    print("Temp tables:", result.temp_tables)
    print("CTEs:", result.ctes)
