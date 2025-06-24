from importlib import import_module
import logging
from types import ModuleType
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class Plugin:
    """Simple wrapper around a plugin module."""

    def __init__(self, module: ModuleType) -> None:
        self.module = module
        self.preprocess: Optional[Callable[[str], str]] = getattr(module, "preprocess", None)
        self.postprocess: Optional[Callable[[str], str]] = getattr(module, "postprocess", None)

    def run_preprocess(self, text: str) -> str:
        if self.preprocess:
            return self.preprocess(text)
        return text

    def run_postprocess(self, text: str) -> str:
        if self.postprocess:
            return self.postprocess(text)
        return text


def load_plugins(names: Optional[List[str]]) -> List[Plugin]:
    """Import and initialize plugins from module names."""
    plugins: List[Plugin] = []
    for name in names or []:
        try:
            module = import_module(name)
        except Exception as exc:
            logger.error("Failed to import plugin '%s': %s", name, exc)
            raise ImportError(f"Cannot import plugin '{name}'") from exc
        plugins.append(Plugin(module))
    return plugins
