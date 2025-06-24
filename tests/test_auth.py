import httpx
import pytest
from moogla import server
from moogla.server import create_app


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
async def test_jwt_auth(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    db = tmp_path / "db.db"
    app = create_app(server_api_key="secret", db_url=f"sqlite:///{db}")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/register", json={"username": "u", "password": "p"})
        assert resp.status_code == 201
        resp = await client.post("/login", json={"username": "u", "password": "p"})
        token = resp.json()["access_token"]
        resp = await client.post(
            "/v1/completions",
            json={"prompt": "abc"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_endpoints(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    db = tmp_path / "db.db"
    app = create_app(server_api_key="secret", db_url=f"sqlite:///{db}")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/register", json={"username": "u", "password": "p"})
        assert resp.status_code == 201

        resp = await client.get("/users", headers={"X-API-Key": "secret"})
        assert resp.status_code == 200
        assert resp.json() == [{"id": 1, "username": "u"}]

        resp = await client.post(
            "/change-password",
            json={"username": "u", "old_password": "p", "new_password": "n"},
            headers={"X-API-Key": "secret"},
        )
        assert resp.status_code == 200

        resp = await client.post("/login", json={"username": "u", "password": "p"})
        assert resp.status_code == 401
        resp = await client.post("/login", json={"username": "u", "password": "n"})
        assert resp.status_code == 200
