# PantheonAI Usage Guide

PantheonAI is a local knowledge builder for Pantheon ERP SQL scripts and documents.

It can:
- scan SQL files
- parse SQL files
- build Markdown knowledge files from SQL
- build Markdown knowledge files from Word and PDF documents
- skip unchanged files with a SHA cache
- clean stale cache entries for deleted files

## Requirements

Install the project dependencies first:

```bash
pip install -r requirements.txt
```

Recommended Python version:
- Python 3.12+

## Input folders

By default, PantheonAI reads from:

- `input/sql` for SQL files
- `input/docs` for Word/PDF files

Supported document types:
- `.sql`
- `.docx`
- `.pdf`

## Output folders

By default, PantheonAI writes Markdown files to:

- `knowledge/sql`
- `knowledge/docs`

It also stores the SHA cache in:

- `.cache/pantheon_ai_sha.json`

## Commands

Run the CLI with:

```bash
python -m pantheon_ai.cli <command>
```

### 1. Scan SQL files

Lists the `.sql` files found in `input/sql`.

```bash
python -m pantheon_ai.cli scan
```

### 2. Parse SQL files

Reads SQL files, parses them, and prints a summary for each one.

```bash
python -m pantheon_ai.cli parse
```

### 3. Build knowledge files

Builds Markdown for:
- SQL files into `knowledge/sql`
- Word/PDF files into `knowledge/docs`

Only changed files are processed.

```bash
python -m pantheon_ai.cli build
```

### 4. Clean stale cache entries

Removes SHA cache entries for files that no longer exist.

Clean everything:

```bash
python -m pantheon_ai.cli clean
```

Clean only SQL cache entries:

```bash
python -m pantheon_ai.cli clean --sql-only
```

Clean only Word/PDF cache entries:

```bash
python -m pantheon_ai.cli clean --docs-only
```

## Examples

### Build only when files changed

```bash
python -m pantheon_ai.cli build
```

### Rebuild after deleting files from the source folders

```bash
python -m pantheon_ai.cli clean
python -m pantheon_ai.cli build
```

## Configuration notes

Current source folders are configured in the CLI by default.
If you want to change them, edit the project settings in the source code or update the CLI arguments.

Example with custom folders:

```bash
python -m pantheon_ai.cli build --input D:\Projects\PantheonAI\input\sql --docs-input D:\Projects\PantheonAI\input\docs --output D:\Projects\PantheonAI\knowledge\sql --docs-output D:\Projects\PantheonAI\knowledge\docs
```

## Typical workflow

1. Put SQL scripts into `input/sql`
2. Put Word/PDF documents into `input/docs`
3. Run `python -m pantheon_ai.cli build`
4. Point AnythingLLM (or another AI tool) to the generated `knowledge` folders

## Notes

- Files that have not changed are skipped by the SHA cache.
- Deleted files are removed from the cache when you run `clean`.
- `clean --sql-only` and `clean --docs-only` let you clean one source type at a time.
