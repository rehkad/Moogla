import asyncio
import os
import httpx
import pytest

from moogla import server, plugins_config


class DummyExecutor:
    def complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        return prompt[::-1]

    async def acomplete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        return prompt[::-1]


@pytest.mark.asyncio
async def test_concurrent_requests(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = server.create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async def call(n: int):
            resp = await client.post("/v1/completions", json={"prompt": str(n)})
            assert resp.status_code == 200
            return resp.json()["choices"][0]["text"]

        results = await asyncio.gather(*(call(i) for i in range(5)))
    assert results == [str(i)[::-1] for i in range(5)]


def test_invalid_db_url(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    monkeypatch.setattr(os, "environ", os.environ.copy())
    with pytest.raises(Exception):
        server.create_app(db_url="invalid://foo")


def test_plugins_db_connection_error(tmp_path, monkeypatch):
    path = tmp_path / "plugins.yaml"
    path.write_text("plugins: []")
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(path))

    def fail_open(*args, **kwargs):
        raise OSError("fail")

    monkeypatch.setattr("builtins.open", fail_open)
    with pytest.raises(OSError):
        plugins_config.get_plugins()
