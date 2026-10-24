"""PantheonAI logging helpers.

Provides a small, consistent logging setup for console and file output.
"""

from __future__ import annotations

from pathlib import Path
import logging
from logging import Logger
from logging.handlers import RotatingFileHandler

try:  # Rich is optional, but recommended for nicer console logs.
    from rich.logging import RichHandler
except Exception:  # pragma: no cover - fallback for minimal environments
    RichHandler = None  # type: ignore[assignment]

_DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str = "pantheon_ai",
    *,
    log_dir: str | Path = "logs",
    level: int = logging.INFO,
    filename: str = "pantheon_ai.log",
) -> Logger:
    """Return a configured logger with console and file handlers.

    The logger is idempotent: calling it multiple times for the same name
    will not duplicate handlers.
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / filename

    formatter = logging.Formatter(
        fmt=_DEFAULT_LOG_FORMAT,
        datefmt=_DEFAULT_DATE_FORMAT,
    )

    if RichHandler is not None:
        console_handler: logging.Handler = RichHandler(
            rich_tracebacks=True,
            markup=False,
            show_time=False,
            show_level=True,
            show_path=False,
        )
    else:
        console_handler = logging.StreamHandler()

    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


__all__ = ["get_logger"]
