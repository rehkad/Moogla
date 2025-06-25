"""Moogla core package."""

from importlib.metadata import version
from .executor import LLMExecutor

__all__ = ["__version__", "LLMExecutor"]
__version__ = version("moogla")
