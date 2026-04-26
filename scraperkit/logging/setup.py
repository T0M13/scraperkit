"""
Structured logging setup for ScraperKit.

Configures:
  - Console handler: human-readable coloured output
  - File handler: JSON-lines for machine parsing
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path


class JsonLineFormatter(logging.Formatter):
    """Emits one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


_LEVEL_COLOURS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET = "\033[0m"


class ColouredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, "")
        prefix = f"{colour}{record.levelname:8}{_RESET}" if sys.stderr.isatty() else record.levelname
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S")
        return f"{ts} {prefix} {record.name}: {record.getMessage()}"


def configure_logging(
    level: str = "INFO",
    log_dir: str | Path | None = None,
    project_name: str = "scraperkit",
) -> None:
    """
    Call once at startup. Sets up console + optional file logging.
    log_dir: if given, writes <project_name>_<date>.jsonl and <project_name>_<date>.log
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers if called multiple times
    if root.handlers:
        root.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(ColouredFormatter())
    root.addHandler(console)

    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")

        # JSON lines for structured parsing / dashboard
        jsonl_path = log_dir / f"{project_name}_{date_str}.jsonl"
        jsonl_handler = logging.FileHandler(jsonl_path, encoding="utf-8")
        jsonl_handler.setFormatter(JsonLineFormatter())
        root.addHandler(jsonl_handler)

        # Plain text log for humans
        plain_path = log_dir / f"{project_name}_{date_str}.log"
        plain_handler = logging.FileHandler(plain_path, encoding="utf-8")
        plain_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
        )
        root.addHandler(plain_handler)

    # Silence overly chatty third-party loggers
    for noisy in ("scrapy", "twisted", "urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
