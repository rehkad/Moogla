import httpx
import pytest
from moogla import server
from moogla.server import create_app


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

    async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]


async def get_token(client, api_key: str | None = None):
    headers = {"X-API-Key": api_key} if api_key else None
    await client.post("/register", json={"username": "u", "password": "p"}, headers=headers)
    resp = await client.post(
        "/login",
        data={"username": "u", "password": "p", "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded", **({"X-API-Key": api_key} if api_key else {})},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_authenticated_access(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(server_api_key="secret", db_url=f"sqlite:///{tmp_path}/db.db")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        token = await get_token(client, "secret")
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc"},
            headers={"X-API-Key": "secret", "Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_missing_api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(server_api_key="secret", db_url=f"sqlite:///{tmp_path}/db.db")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        token = await get_token(client, "secret")
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_and_login(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(db_url=f"sqlite:///{tmp_path}/db.db")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/register", json={"username": "bob", "password": "pw"}
        )
        assert resp.status_code == 200
        resp = await client.post(
            "/login",
            data={"username": "bob", "password": "pw", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
