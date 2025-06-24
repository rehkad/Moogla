import os
import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
from moogla.server import create_app


def test_secret_required_in_production(monkeypatch):
    monkeypatch.delenv("MOOGLA_JWT_SECRET", raising=False)
    monkeypatch.setenv("MOOGLA_ENV", "production")
    with pytest.raises(RuntimeError):
        create_app()


def test_cors_origins_env(monkeypatch):
    monkeypatch.setenv("MOOGLA_CORS_ORIGINS", "http://example.com")
    app = create_app()
    cors = [m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"]
    assert cors and cors[0].kwargs["allow_origins"] == ["http://example.com"]
