import asyncio
import inspect
import logging
import sys
from importlib import import_module, invalidate_caches, reload
from types import ModuleType
from typing import Callable, List, Optional

from . import plugins_config

logger = logging.getLogger(__name__)


class Plugin:
    """Simple wrapper around a plugin module."""

    def __init__(self, module: ModuleType) -> None:
        self.module = module
        self.preprocess: Optional[Callable[[str], str]] = getattr(
            module, "preprocess", None
        )
        self.preprocess_async: Optional[Callable[[str], str]] = getattr(
            module, "preprocess_async", None
        )
        self.postprocess: Optional[Callable[[str], str]] = getattr(
            module, "postprocess", None
        )
        self.postprocess_async: Optional[Callable[[str], str]] = getattr(
            module, "postprocess_async", None
        )
        self.teardown: Optional[Callable[[], None]] = getattr(module, "teardown", None)
        self.teardown_async: Optional[Callable[[], None]] = getattr(
            module, "teardown_async", None
        )
        self.order: int = getattr(module, "order", 0)

    async def run_preprocess(self, text: str) -> str:
        func = self.preprocess_async or self.preprocess
        if func:
            if inspect.iscoroutinefunction(func):
                return await func(text)
            return func(text)
        return text

    async def run_postprocess(self, text: str) -> str:
        func = self.postprocess_async or self.postprocess
        if func:
            if inspect.iscoroutinefunction(func):
                return await func(text)
            return func(text)
        return text

    async def run_teardown(self) -> None:
        """Invoke teardown hooks if defined."""
        func = self.teardown_async or self.teardown
        if func:
            if inspect.iscoroutinefunction(func):
                await func()
            else:
                func()


def load_plugins(
    names: Optional[List[str]], *, reload_modules: bool = False
) -> List[Plugin]:
    """Import and initialize plugins from module names or configured store."""
    if not names:
        names = plugins_config.get_plugins()
    plugins: List[Plugin] = []
    for name in names or []:
        try:
            if reload_modules:
                invalidate_caches()
                if name in sys.modules:
                    module = reload(sys.modules[name])
                else:
                    module = import_module(name)
            else:
                module = import_module(name)
        except Exception as exc:
            logger.error("Failed to import plugin '%s': %s", name, exc)
            raise ImportError(f"Cannot import plugin '{name}'") from exc

        settings = plugins_config.get_plugin_settings(name)
        setup_func = getattr(module, "setup", None)
        if setup_func:
            try:
                setup_func(settings)
            except Exception as exc:  # pragma: no cover - pass through
                logger.error("Failed to setup plugin '%s': %s", name, exc)
                raise

        setup_async = getattr(module, "setup_async", None)
        if setup_async:
            try:
                if inspect.iscoroutinefunction(setup_async):
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        asyncio.run(setup_async(settings))
                    else:
                        loop.create_task(setup_async(settings))
                else:
                    setup_async(settings)
            except Exception as exc:  # pragma: no cover - pass through
                logger.error("Failed to setup plugin '%s': %s", name, exc)
                raise

        plugin = Plugin(module)
        plugins.append(plugin)
        logger.info("Loaded plugin '%s'", name)

    plugins.sort(key=lambda p: p.order)
    return plugins
