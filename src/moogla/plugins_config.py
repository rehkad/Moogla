import os
import json
import sqlite3
from pathlib import Path
from typing import List


def _get_path() -> Path:
    env = os.getenv("MOOGLA_PLUGIN_DB")
    return Path(env) if env else Path.home() / ".cache" / "moogla" / "plugins.db"


def _ensure_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)"
    )
    return conn


def _set_plugins(names: List[str], path: Path) -> None:
    conn = _ensure_db(path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO config(key, value) VALUES('plugins', ?)",
            (json.dumps(names),),
        )
        conn.commit()
    finally:
        conn.close()


def get_plugins() -> List[str]:
    path = _get_path()
    conn = _ensure_db(path)
    try:
        row = conn.execute("SELECT value FROM config WHERE key='plugins'").fetchone()
        return json.loads(row[0]) if row else []
    finally:
        conn.close()


def add_plugin(name: str) -> None:
    names = get_plugins()
    if name not in names:
        names.append(name)
        _set_plugins(names, _get_path())


def remove_plugin(name: str) -> None:
    names = get_plugins()
    if name in names:
        names.remove(name)
        _set_plugins(names, _get_path())
