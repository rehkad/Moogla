import os
import httpx
import pytest

from moogla import server
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

    async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]


@pytest.mark.asyncio
async def test_plugin_management_endpoints(monkeypatch, tmp_path):
    db = tmp_path / "plugins.db"
    monkeypatch.setenv("MOOGLA_PLUGIN_DB", str(db))
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(db_url=f"sqlite:///{tmp_path}/db.db")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/plugins")
        assert resp.status_code == 200
        assert resp.json()["plugins"] == []

        resp = await client.post("/plugins", json={"name": "tests.dummy_plugin"})
        assert resp.status_code == 201
        assert "tests.dummy_plugin" in resp.json()["plugins"]

        resp = await client.post("/v1/completions", json={"prompt": "abc"})
        assert resp.json()["choices"][0]["text"] == "!!CBA!!"

        resp = await client.delete("/plugins/tests.dummy_plugin")
        assert resp.status_code == 204

        resp = await client.post("/v1/completions", json={"prompt": "abc"})
        assert resp.json()["choices"][0]["text"] == "cba"


@pytest.mark.asyncio
async def test_enable_invalid_plugin(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/plugins", json={"name": "no.such.module"})
    assert resp.status_code == 400
