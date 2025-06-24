import httpx
import pytest
from moogla import server
from moogla.server import create_app


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

    async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]


@pytest.mark.asyncio
async def test_authenticated_access(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(server_api_key="secret")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc"},
            headers={"X-API-Key": "secret"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_missing_api_key(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(server_api_key="secret")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_existing_user(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/register",
            json={"username": "alice", "password": "password"},
        )
        resp = await client.post(
            "/register",
            json={"username": "alice", "password": "password"},
        )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "User exists"}
