import os
import json
import pytest
import httpx
from fastapi.testclient import TestClient

from moogla import server
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class DummyExecutor:
    def __init__(self) -> None:
        self.last = {}

    def complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        self.last = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        return prompt[::-1]

    async def acomplete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        self.last = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        return prompt[::-1]

    async def astream(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ):
        self.last = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        text = prompt[::-1]
        for i in range(0, len(text), 2):
            yield text[i : i + 2]


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
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}], "stream": True},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    lines = [l for l in resp.text.splitlines() if l.strip()]
    reply = "".join(json.loads(l)["choices"][0]["delta"]["content"] for l in lines)
    assert reply == "olleh"


@pytest.mark.asyncio
async def test_completion_stream(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc", "stream": True},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    lines = [l for l in resp.text.splitlines() if l.strip()]
    reply = "".join(json.loads(l)["choices"][0]["delta"]["content"] for l in lines)
    assert reply == "cba"


@pytest.mark.asyncio
async def test_option_forwarding(monkeypatch):
    dummy = DummyExecutor()
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: dummy)
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/v1/completions",
            json={
                "prompt": "abc",
                "max_tokens": 5,
                "temperature": 0.5,
                "top_p": 0.9,
            },
        )
    assert dummy.last == {"max_tokens": 5, "temperature": 0.5, "top_p": 0.9}


def test_root_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Moogla Chat" in resp.text
