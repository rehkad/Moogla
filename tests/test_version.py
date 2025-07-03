import importlib
from importlib import metadata

from fastapi.testclient import TestClient

from moogla import __version__
from moogla.server import create_app


def test_version_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/version")
    assert resp.status_code == 200
    assert resp.json() == {"version": __version__}


def test_version_fallback(monkeypatch):
    """Package version should default when metadata is missing."""

    def raise_not_found(_: str):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", raise_not_found)
    mod = importlib.reload(importlib.import_module("moogla"))
    assert mod.__version__ == "0.0.0"
