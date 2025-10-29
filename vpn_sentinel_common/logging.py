"""Small logging helpers used across the project.

Keep this intentionally tiny and dependency-free so tests and CI can import it
without adding runtime dependencies.
"""
from __future__ import annotations

import logging
import sys


def _configure_once():
    # Basic config: stream to stdout with human-friendly format.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


def log_info(component: str, msg: str) -> None:
    _configure_once()
    logging.info(f"{component} | {msg}")


def log_warn(component: str, msg: str) -> None:
    _configure_once()
    logging.warning(f"{component} | {msg}")


def log_error(component: str, msg: str) -> None:
    _configure_once()
    logging.error(f"{component} | {msg}")
