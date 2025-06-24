from dataclasses import dataclass
from pathlib import Path
import os
import tomllib
from typing import Optional

@dataclass
class Config:
    """Runtime configuration parameters."""

    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    api_base: Optional[str] = None


def load_config(path: Optional[str | Path] = None) -> Config:
    """Load configuration from ``path`` and merge environment variables."""
    file_path = Path(os.getenv("MOOGLA_CONFIG", path or "config.toml"))
    data: dict[str, object] = {}
    if file_path.is_file():
        with open(file_path, "rb") as fh:
            data = tomllib.load(fh)

    cfg_dict = {
        "model": "gpt-3.5-turbo",
        "api_key": None,
        "api_base": None,
        **data,
    }

    overrides = {
        "model": os.getenv("MOOGLA_MODEL"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "api_base": os.getenv("OPENAI_API_BASE"),
    }
    for key, value in overrides.items():
        if value is not None:
            cfg_dict[key] = value

    return Config(**cfg_dict)
