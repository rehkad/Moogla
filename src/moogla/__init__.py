"""Moogla core package."""

from __future__ import annotations

import logging
import os

from .executor import LLMExecutor

__all__ = ["__version__", "LLMExecutor", "configure_logging"]
__version__ = "0.0.1"


def configure_logging(level: str | int | None = None) -> None:
    """Configure basic logging for the package.

    Parameters
    ----------
    level: Optional log level to set. When ``None`` the ``MOOGLA_LOG_LEVEL``
        environment variable is consulted and defaults to ``"INFO"``.
    """

    if logging.getLogger().handlers:
        # Respect existing configuration provided by the application.
        return

    resolved_level = level or os.getenv("MOOGLA_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

