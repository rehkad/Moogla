import httpx
import pytest

from moogla import server
from moogla.server import create_app


class DummyExecutor:
    def complete(self, prompt: str, max_tokens=None, temperature=None, top_p=None):
        return prompt

    async def acomplete(
        self, prompt: str, max_tokens=None, temperature=None, top_p=None
    ):
        return prompt

    async def astream(self, prompt: str, max_tokens=None, temperature=None, top_p=None):
        yield prompt


@pytest.mark.asyncio
async def test_cors_headers(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(cors_origins="http://example.com")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health", headers={"Origin": "http://example.com"})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://example.com"
    assert resp.headers["access-control-allow-credentials"] == "true"
