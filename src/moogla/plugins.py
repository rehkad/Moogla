from importlib import import_module
from types import ModuleType
from typing import Callable, List, Optional


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
        module = import_module(name)
        plugins.append(Plugin(module))
    return plugins
