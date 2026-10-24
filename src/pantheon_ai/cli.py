"""PantheonAI command-line interface.

This module provides a small CLI for Sprint 1:
- scan SQL files
- parse SQL files
- build Markdown knowledge documents
- build Word/PDF knowledge documents
- skip unchanged files using a SHA cache
- clean stale SHA cache entries

Usage examples
--------------
python -m pantheon_ai.cli scan
python -m pantheon_ai.cli parse
python -m pantheon_ai.cli build
python -m pantheon_ai.cli clean
python -m pantheon_ai.cli clean --sql-only
python -m pantheon_ai.cli clean --docs-only
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable

from pantheon_ai.analyzers.sql_parser import SqlParser
from pantheon_ai.collectors.pdf_collector import PdfCollector
from pantheon_ai.collectors.sql_collector import SqlCollector, SqlDocument
from pantheon_ai.collectors.word_collector import WordCollector
from pantheon_ai.generators.document_markdown_generator import DocumentMarkdownGenerator
from pantheon_ai.generators.markdown_generator import MarkdownGenerator
from pantheon_ai.utils.logger import get_logger
from pantheon_ai.utils.sha_cache import ShaCache

DEFAULT_SQL_INPUT_DIR = Path("input") / "sql"
DEFAULT_DOC_INPUT_DIR = Path("input") / "docs"
DEFAULT_SQL_OUTPUT_DIR = Path("knowledge") / "sql"
DEFAULT_DOC_OUTPUT_DIR = Path("knowledge") / "docs"
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_CACHE_FILE = Path(".cache") / "pantheon_ai_sha.json"


def build_parser() -> ArgumentParser:
    """Create and return the top-level argument parser."""

    parser = ArgumentParser(prog="pantheon-ai", description="PantheonAI Sprint 1 CLI")
    parser.add_argument(
        "--input",
        dest="input_dir",
        default=str(DEFAULT_SQL_INPUT_DIR),
        help="Input directory containing .sql files (default: input/sql)",
    )
    parser.add_argument(
        "--docs-input",
        dest="docs_input_dir",
        default=str(DEFAULT_DOC_INPUT_DIR),
        help="Input directory containing Word/PDF files (default: input/docs)",
    )
    parser.add_argument(
        "--output",
        dest="output_dir",
        default=str(DEFAULT_SQL_OUTPUT_DIR),
        help="Output directory for SQL Markdown files (default: knowledge/sql)",
    )
    parser.add_argument(
        "--docs-output",
        dest="docs_output_dir",
        default=str(DEFAULT_DOC_OUTPUT_DIR),
        help="Output directory for Word/PDF Markdown files (default: knowledge/docs)",
    )
    parser.add_argument(
        "--cache-file",
        dest="cache_file",
        default=str(DEFAULT_CACHE_FILE),
        help="JSON file used to track SHA hashes and skip unchanged files",
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
    subparsers.add_parser("build", help="Build SQL and document Markdown knowledge files")

    clean_parser = subparsers.add_parser("clean", help="Clean stale SHA cache entries")
    clean_group = clean_parser.add_mutually_exclusive_group()
    clean_group.add_argument(
        "--sql-only",
        action="store_true",
        help="Clean only SQL cache entries",
    )
    clean_group.add_argument(
        "--docs-only",
        action="store_true",
        help="Clean only Word/PDF cache entries",
    )

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

    sql_input_dir = Path(args.input_dir)
    docs_input_dir = Path(args.docs_input_dir)
    sql_output_dir = Path(args.output_dir)
    docs_output_dir = Path(args.docs_output_dir)
    cache_file = Path(args.cache_file)

    sql_collector = SqlCollector(sql_input_dir, cache_file=cache_file)
    sql_parser = SqlParser()
    sql_generator = MarkdownGenerator(sql_output_dir)
    doc_generator = DocumentMarkdownGenerator(docs_output_dir)

    if args.command == "scan":
        _run_scan(sql_collector, logger)
        return 0

    if args.command == "parse":
        _run_parse(sql_collector, sql_parser, logger)
        return 0

    if args.command == "build":
        _run_build(sql_collector, sql_parser, sql_generator, logger)
        _run_build_documents(docs_input_dir, doc_generator, cache_file, logger)
        return 0

    if args.command == "clean":
        _run_clean(
            sql_input_dir=sql_input_dir,
            docs_input_dir=docs_input_dir,
            cache_file=cache_file,
            logger=logger,
            sql_only=args.sql_only,
            docs_only=args.docs_only,
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_scan(collector: SqlCollector, logger) -> None:
    files = collector.scan()
    logger.info("Found %s SQL files", len(files))
    for file_path in files:
        logger.info("SQL file: %s", file_path)


def _run_parse(collector: SqlCollector, sql_parser: SqlParser, logger) -> None:
    documents = collector.collect(changed_only=False)
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
    documents = collector.collect(changed_only=True)
    logger.info("Collected %s changed SQL documents", len(documents))

    written = 0
    for document in documents:
        sql_object = sql_parser.parse(document)
        relative_path = _relative_output_path(document)
        output_path = generator.generate(
            sql_object,
            relative_path=relative_path,
            source_path=document.absolute_path,
        )
        written += 1
        logger.info("Wrote SQL Markdown: %s", output_path)

    logger.info("SQL build complete. Markdown files written: %s", written)


def _run_build_documents(
    input_dir: Path,
    generator: DocumentMarkdownGenerator,
    cache_file: Path,
    logger,
) -> None:
    if not input_dir.exists():
        logger.warning("Document input folder does not exist: %s", input_dir)
        return

    word_collector = WordCollector(input_dir, cache_file=cache_file)
    pdf_collector = PdfCollector(input_dir, cache_file=cache_file)

    documents = word_collector.collect(changed_only=True) + pdf_collector.collect(changed_only=True)
    logger.info("Collected %s changed non-SQL documents", len(documents))

    written = 0
    for document in documents:
        relative_path = _relative_output_path(document)
        output_path = generator.generate(document, relative_path=relative_path)
        written += 1
        logger.info("Wrote document Markdown: %s", output_path)

    logger.info("Document build complete. Markdown files written: %s", written)


def _run_clean(
    *,
    sql_input_dir: Path,
    docs_input_dir: Path,
    cache_file: Path,
    logger,
    sql_only: bool,
    docs_only: bool,
) -> None:
    cache = ShaCache(cache_file)
    removed_total = 0

    if not sql_only and not docs_only:
        removed_total += _prune_sql_cache(cache, sql_input_dir)
        removed_total += _prune_docs_cache(cache, docs_input_dir)
    elif sql_only:
        removed_total += _prune_sql_cache(cache, sql_input_dir)
    elif docs_only:
        removed_total += _prune_docs_cache(cache, docs_input_dir)

    cache.save()
    logger.info("Cache clean complete. Removed %s stale entries.", removed_total)


def _prune_sql_cache(cache: ShaCache, sql_input_dir: Path) -> int:
    if not sql_input_dir.exists():
        return 0
    collector = SqlCollector(sql_input_dir)
    active_keys = _scan_keys(sql_input_dir, collector.scan())
    return cache.prune(collector.CACHE_NAMESPACE, active_keys)


def _prune_docs_cache(cache: ShaCache, docs_input_dir: Path) -> int:
    if not docs_input_dir.exists():
        return 0

    removed_total = 0

    word_collector = WordCollector(docs_input_dir)
    removed_total += cache.prune(
        word_collector.CACHE_NAMESPACE,
        _scan_keys(docs_input_dir, word_collector.scan()),
    )

    pdf_collector = PdfCollector(docs_input_dir)
    removed_total += cache.prune(
        pdf_collector.CACHE_NAMESPACE,
        _scan_keys(docs_input_dir, pdf_collector.scan()),
    )

    return removed_total


def _scan_keys(root: Path, files: Iterable[Path]) -> list[str]:
    return [path.relative_to(root).as_posix() for path in files]


def _relative_output_path(document: SqlDocument | object) -> str:
    """Map an input file location to a mirrored knowledge path."""

    relative = Path(getattr(document, "relative_path", ""))
    if str(relative) == ".":
        return ""
    return str(relative)


if __name__ == "__main__":
    raise SystemExit(main())
