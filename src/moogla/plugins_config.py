import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

PLUGIN_FILE_PATH: Optional[Path] = None


def set_plugin_file(path: Optional[str]) -> None:
    """Override the location of the plugin configuration file."""
    global PLUGIN_FILE_PATH
    PLUGIN_FILE_PATH = Path(path) if path else None


def _get_path() -> Path:
    env = os.getenv("MOOGLA_PLUGIN_FILE")
    if env:
        return Path(env)
    if PLUGIN_FILE_PATH is not None:
        return PLUGIN_FILE_PATH
    return Path.home() / ".cache" / "moogla" / "plugins.yaml"


def _load() -> Dict[str, Any]:
    path = _get_path()
    if not path.exists():
        return {}
    with open(path, "r") as f:
        if path.suffix in {".yaml", ".yml"}:
            return yaml.safe_load(f) or {}
        return json.load(f)


def _save(data: Dict[str, Any]) -> None:
    path = _get_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        if path.suffix in {".yaml", ".yml"}:
            yaml.safe_dump(data, f)
        else:
            json.dump(data, f, indent=2)


def get_plugins() -> List[str]:
    data = _load()
    plugins = data.get("plugins")
    if isinstance(plugins, list):
        return plugins
    if isinstance(data, list):
        return data
    return []


def add_plugin(name: str, **settings: Any) -> None:
    data = _load()
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
    _save(data)


def remove_plugin(name: str) -> None:
    data = _load()
    plugins = data.get("plugins")
    if isinstance(plugins, list) and name in plugins:
        plugins.remove(name)
    if isinstance(data.get("settings"), dict):
        data["settings"].pop(name, None)
    _save(data)
