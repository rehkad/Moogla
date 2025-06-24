"""Moogla core package."""

from .executor import LLMExecutor
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, serialize=True)

__all__ = ["__version__", "LLMExecutor"]
__version__ = "0.0.1"
