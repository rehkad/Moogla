from importlib import import_module, metadata
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
    """Import and initialize plugins from module names and entry points."""
    plugins: List[Plugin] = []
    loaded: set[str] = set()

    for name in names or []:
        try:
            module = import_module(name)
        except Exception as exc:
            logger.error("Failed to import plugin '%s': %s", name, exc)
            raise ImportError(f"Cannot import plugin '{name}'") from exc
        plugins.append(Plugin(module))
        loaded.add(module.__name__)

    try:
        entries = metadata.entry_points(group="moogla.plugins")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to read entry points: %s", exc)
        entries = []

    for ep in entries:
        try:
            module = ep.load()
        except Exception as exc:
            logger.error("Failed to load plugin '%s': %s", ep.value, exc)
            raise ImportError(f"Cannot load plugin '{ep.value}'") from exc
        if module.__name__ not in loaded:
            plugins.append(Plugin(module))
            loaded.add(module.__name__)

    return plugins
