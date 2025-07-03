"""Moogla core package."""

from importlib.metadata import PackageNotFoundError, version

from .executor import LLMExecutor

__all__ = ["__version__", "LLMExecutor"]
try:
    __version__ = version("moogla")
except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.0.0"
