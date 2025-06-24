# Authentication utilities for Moogla

from __future__ import annotations

import os
from typing import Optional

_db_url: Optional[str] = None
_secret_key: Optional[str] = None


def init(db_url: str, secret_key: Optional[str] = None) -> None:
    """Initialize authentication backend.

    Parameters
    ----------
    db_url:
        Path to the user database, e.g. ``sqlite:///users.db``.
    secret_key:
        Key used to sign session tokens. Defaults to the ``MOOGLA_SECRET_KEY``
        environment variable or ``"secret"`` if unset.
    """
    global _db_url, _secret_key
    _db_url = db_url
    _secret_key = secret_key or os.getenv("MOOGLA_SECRET_KEY", "secret")


def get_db_url() -> Optional[str]:
    """Return the configured database URL."""
    return _db_url


def get_secret_key() -> Optional[str]:
    """Return the secret key used for signing."""
    return _secret_key
