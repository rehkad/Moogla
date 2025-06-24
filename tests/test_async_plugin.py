import os
import httpx
import pytest

from moogla.server import create_app
from moogla import server

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

    async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

    async def astream(self, prompt: str, max_tokens: int = 16):
        text = prompt[::-1]
        for i in range(0, len(text), 2):
            yield text[i : i + 2]


@pytest.mark.asyncio
async def test_async_plugin(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(["tests.async_plugin"])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/completions", json={"prompt": "hi"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "<IH>"


@pytest.mark.asyncio
async def test_plugin_order(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(["tests.order_plugin_a", "tests.order_plugin_b"])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/completions", json={"prompt": "x"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "abx"
