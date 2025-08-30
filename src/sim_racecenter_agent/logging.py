"""Centralized logging configuration for the project.

All application and tool modules should import `get_logger` from here
to ensure logging goes to stderr (important for MCP stdio transport)
and shares consistent formatting & level control.

Environment variables:
  LOG_LEVEL  - root logging level (default INFO)
  LOG_FORMAT - optional override of log format

Use:
    from sim_racecenter_agent.logging import get_logger
    logger = get_logger(__name__)
    logger.info("message")
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_CONFIGURED = False
_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: Optional[str] = None, fmt: Optional[str] = None) -> None:
    """Idempotently configure root logger to emit to stderr only.

    Subsequent calls are no-ops unless level/format overrides are supplied.
    """
    global _CONFIGURED
    root = logging.getLogger()
    if not level:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if not fmt:
        fmt = os.environ.get("LOG_FORMAT", _DEFAULT_FORMAT)

    # If already configured, allow dynamic level change then return.
    if _CONFIGURED:
        root.setLevel(getattr(logging, level, logging.INFO))
        return

    # Remove any pre-existing handlers (e.g., from test runner auto-config)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger, ensuring global configuration is applied first."""
    configure_logging()
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]
