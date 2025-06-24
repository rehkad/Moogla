import os
import json
import pytest
import httpx
from fastapi.testclient import TestClient

from moogla import server
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

    async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]


@pytest.mark.asyncio
async def test_chat_completion(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "olleh"


@pytest.mark.asyncio
async def test_completion_endpoint(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "cba"


@pytest.mark.asyncio
async def test_plugins(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(["tests.dummy_plugin"])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "!!OLLEH!!"


@pytest.mark.asyncio
async def test_chat_completion_stream(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}], "stream": True},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    lines = [line for line in resp.text.splitlines() if line.strip()]
    reply = "".join(
        json.loads(line)["choices"][0]["delta"]["content"] for line in lines
    )
    assert reply == "olleh"


@pytest.mark.asyncio
async def test_completion_stream(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc", "stream": True},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    lines = [line for line in resp.text.splitlines() if line.strip()]
    reply = "".join(
        json.loads(line)["choices"][0]["delta"]["content"] for line in lines
    )
    assert reply == "cba"


def test_root_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Moogla Chat" in resp.text
