import asyncio
import os
import sqlite3
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


def test_plugins_db_connection_error(monkeypatch):
    def fail_connect(*args, **kwargs):
        raise sqlite3.OperationalError("fail")

    monkeypatch.setattr(plugins_config.sqlite3, "connect", fail_connect)
    with pytest.raises(sqlite3.OperationalError):
        plugins_config.get_plugins()
