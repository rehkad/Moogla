"""Utility helpers for loading and saving plugin configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError


class PluginConfigModel(BaseModel):
    """Schema for plugin configuration files."""

    plugins: List[str] = []
    settings: Dict[str, Dict[str, Any]] = {}

    model_config = ConfigDict(extra="forbid")


class PluginStore:
    """Persist and retrieve plugin configuration from disk."""

    DEFAULT_FILE = Path.home() / ".cache" / "moogla" / "plugins.yaml"

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or self.DEFAULT_FILE

    def set_path(self, path: Optional[str]) -> None:
        self.path = Path(path) if path else self.DEFAULT_FILE

    def get_path(self) -> Path:
        """Return the configured plugin file path."""
        return self._resolve_path()

    def _resolve_path(self) -> Path:
        env = os.getenv("MOOGLA_PLUGIN_FILE")
        if env:
            return Path(env)
        return self.path

    def load(self) -> Dict[str, Any]:
        path = self._resolve_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix in {".yaml", ".yml"}:
                    raw = yaml.safe_load(f) or {}
                else:
                    raw = json.load(f)
            if isinstance(raw, list):
                raw = {"plugins": raw}
            data = PluginConfigModel.model_validate(raw)
            return data.model_dump()
        except (
            OSError,
            json.JSONDecodeError,
            yaml.YAMLError,
            ValidationError,
        ) as e:  # pragma: no cover - file errors
            raise RuntimeError(f"Failed to load plugin config: {e}") from e

    def save(self, data: Dict[str, Any]) -> None:
        path = self._resolve_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                if path.suffix in {".yaml", ".yml"}:
                    yaml.safe_dump(data, f)
                else:
                    json.dump(data, f, indent=2, sort_keys=True)
            os.replace(tmp, path)
        except OSError as e:  # pragma: no cover - filesystem errors
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to save plugin config: {e}") from e

    def get_plugins(self) -> List[str]:
        data = self.load()
        plugins = data.get("plugins")
        if isinstance(plugins, list):
            return plugins
        if isinstance(data, list):
            return data
        return []

    def add_plugin(self, name: str, **settings: Any) -> None:
        data = self.load()
        plugins = data.get("plugins")
        if plugins is None:
            if isinstance(data, list):
                plugins = data
            else:
                plugins = []
            data["plugins"] = plugins
        if name not in plugins:
            plugins.append(name)
        if settings:
            data.setdefault("settings", {}).setdefault(name, {}).update(settings)
        self.save(data)

    def remove_plugin(self, name: str) -> None:
        data = self.load()
        plugins = data.get("plugins")
        if isinstance(plugins, list) and name in plugins:
            plugins.remove(name)
        if isinstance(data.get("settings"), dict):
            data["settings"].pop(name, None)
        self.save(data)

    def clear_plugins(self) -> None:
        self.save({})

    def get_plugin_settings(self, name: str) -> Dict[str, Any]:
        data = self.load()
        settings = data.get("settings")
        if isinstance(settings, dict):
            value = settings.get(name)
            if isinstance(value, dict):
                return value
        return {}

    def get_all_plugin_settings(self) -> Dict[str, Dict[str, Any]]:
        data = self.load()
        settings = data.get("settings")
        if isinstance(settings, dict):
            return {k: v for k, v in settings.items() if isinstance(v, dict)}
        return {}


_default = PluginStore()


def set_plugin_file(path: Optional[str]) -> None:
    """Override the location of the plugin configuration file."""
    _default.set_path(path)


def get_plugins() -> List[str]:
    return _default.get_plugins()


def add_plugin(name: str, **settings: Any) -> None:
    _default.add_plugin(name, **settings)


def remove_plugin(name: str) -> None:
    _default.remove_plugin(name)


def clear_plugins() -> None:
    _default.clear_plugins()


def get_plugin_settings(name: str) -> Dict[str, Any]:
    return _default.get_plugin_settings(name)


def get_all_plugin_settings() -> Dict[str, Dict[str, Any]]:
    return _default.get_all_plugin_settings()


def get_path() -> Path:
    """Return the active plugin configuration file path."""
    return _default.get_path()
