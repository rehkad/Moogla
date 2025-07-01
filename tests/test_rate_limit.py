import os

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from moogla import server
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


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

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_rate_limit(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())

    class MemoryLimiter:
        def __init__(self, times):
            self.times = times
            self.hits = {}

        async def __call__(self, request: Request, response: Response):
            ip = request.client.host
            count = self.hits.get(ip, 0) + 1
            self.hits[ip] = count
            if count > self.times:
                raise HTTPException(status_code=429, detail="Too Many Requests")

    monkeypatch.setattr(
        server, "RateLimiter", lambda times=1, seconds=60: MemoryLimiter(times)
    )
    monkeypatch.setattr(
        server,
        "FastAPILimiter",
        type(
            "Dummy", (), {"init": lambda *a, **k: None, "close": lambda *a, **k: None}
        ),
    )
    app = create_app(rate_limit=1, redis_url="redis://test")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/v1/completions", json={"prompt": "abc"})
        resp = await client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 429


def test_no_rate_limit(monkeypatch):
    """Ensure Redis is not contacted when rate limiting is disabled."""

    def fail_init(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("init called")

    def fail_from_url(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("redis accessed")

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    monkeypatch.setattr(server.FastAPILimiter, "init", fail_init)
    monkeypatch.setattr(server.FastAPILimiter, "close", lambda *a, **k: None)
    monkeypatch.setattr("redis.asyncio.from_url", fail_from_url)

    with TestClient(create_app(rate_limit=None, redis_url="redis://test")) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
