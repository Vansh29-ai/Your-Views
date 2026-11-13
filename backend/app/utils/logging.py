"""Structured-ish logging setup for the backend."""

from __future__ import annotations

import logging
import sys

from app.config.settings import settings


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "urllib3", "sentence_transformers", "transformers", "filelock"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
