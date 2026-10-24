"""PantheonAI command-line interface.

This module provides a small CLI for Sprint 1:
- scan SQL files
- parse SQL files
- build Markdown knowledge documents

Usage examples
--------------
python -m pantheon_ai.cli scan
python -m pantheon_ai.cli parse
python -m pantheon_ai.cli build
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable

from pantheon_ai.analyzers.sql_parser import SqlParser
from pantheon_ai.collectors.sql_collector import SqlCollector, SqlDocument
from pantheon_ai.generators.markdown_generator import MarkdownGenerator
from pantheon_ai.utils.logger import get_logger

DEFAULT_INPUT_DIR = Path("input") / "sql"
DEFAULT_OUTPUT_DIR = Path("knowledge") / "sql"
DEFAULT_LOG_DIR = Path("logs")


def build_parser() -> ArgumentParser:
    """Create and return the top-level argument parser."""

    parser = ArgumentParser(prog="pantheon-ai", description="PantheonAI Sprint 1 CLI")
    parser.add_argument(
        "--input",
        dest="input_dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Input directory containing .sql files (default: input/sql)",
    )
    parser.add_argument(
        "--output",
        dest="output_dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for Markdown knowledge files (default: knowledge/sql)",
    )
    parser.add_argument(
        "--log-dir",
        dest="log_dir",
        default=str(DEFAULT_LOG_DIR),
        help="Directory for log files (default: logs)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="Scan SQL files and print a summary")
    subparsers.add_parser("parse", help="Scan and parse SQL files")
    subparsers.add_parser("build", help="Build Markdown knowledge documents")

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the CLI and return an exit code."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    logger = get_logger(
        "pantheon_ai",
        log_dir=args.log_dir,
        level=10 if args.verbose else 20,
    )

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    collector = SqlCollector(input_dir)
    sql_parser = SqlParser()
    generator = MarkdownGenerator(output_dir)

    if args.command == "scan":
        _run_scan(collector, logger)
        return 0

    if args.command == "parse":
        _run_parse(collector, sql_parser, logger)
        return 0

    if args.command == "build":
        _run_build(collector, sql_parser, generator, logger)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_scan(collector: SqlCollector, logger) -> None:
    files = collector.scan()
    logger.info("Found %s SQL files", len(files))
    for file_path in files:
        logger.info("SQL file: %s", file_path)


def _run_parse(collector: SqlCollector, sql_parser: SqlParser, logger) -> None:
    documents = collector.collect()
    logger.info("Collected %s SQL documents", len(documents))

    for document in documents:
        sql_object = sql_parser.parse(document)
        summary = sql_parser.summary(sql_object)
        logger.info(
            "Parsed %s | Type=%s | Schema=%s | Name=%s | Tables=%s | Execs=%s",
            document.filename,
            summary["Type"],
            summary["Schema"],
            summary["Name"],
            summary["Tables"],
            summary["Execs"],
        )


def _run_build(
    collector: SqlCollector,
    sql_parser: SqlParser,
    generator: MarkdownGenerator,
    logger,
) -> None:
    documents = collector.collect()
    logger.info("Collected %s SQL documents", len(documents))

    written = 0
    for document in documents:
        sql_object = sql_parser.parse(document)
        relative_path = _relative_output_path(document)
        output_path = generator.generate(sql_object, relative_path=relative_path)
        written += 1
        logger.info("Wrote Markdown: %s", output_path)

    logger.info("Build complete. Markdown files written: %s", written)


def _relative_output_path(document: SqlDocument) -> str:
    """Map an input SQL file location to a mirrored knowledge path."""

    relative = Path(document.relative_path)
    if str(relative) == ".":
        return ""
    return str(relative)


if __name__ == "__main__":
    raise SystemExit(main())
