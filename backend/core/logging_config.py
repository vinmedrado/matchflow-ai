from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: int | str = logging.INFO,
    *,
    log_to_file: Optional[bool] = None,
    log_file: str | Path = "logs/backend.log",
    force: bool = False,
) -> None:
    """Configure standardized logging for MatchFlow Analytics.

    Console logging is enabled by default. Runtime file logging is opt-in through
    MATCHFLOW_LOG_TO_FILE=true or by passing log_to_file=True, so release ZIPs do
    not include generated log files.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    if log_to_file is None:
        log_to_file = os.getenv("MATCHFLOW_LOG_TO_FILE", "false").strip().lower() in {"1", "true", "yes"}

    root_logger = logging.getLogger()
    if root_logger.handlers and not force:
        root_logger.setLevel(level)
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
        return

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_to_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        handlers=handlers,
        force=force,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module logger using the global MatchFlow logging format."""
    configure_logging()
    return logging.getLogger(name)
