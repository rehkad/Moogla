import importlib
import os

import httpx
import pytest

from moogla import server
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class DummyExecutor:
    async def acomplete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        return prompt[::-1]

    async def astream(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ):
        text = prompt[::-1]
        for i in range(0, len(text), 2):
            yield text[i : i + 2]


@pytest.mark.asyncio
async def test_teardown_async_called(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    plugin = importlib.import_module("tests.teardown_plugin")
    plugin.called = 0
    app = create_app(["tests.teardown_plugin"])
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert plugin.called == 1
