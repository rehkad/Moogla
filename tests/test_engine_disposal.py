import pytest
import httpx

from moogla import server


class DummyEngine:
    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


class DummyExecutor:
    async def acomplete(self, *a, **kw):
        return ""

    async def astream(self, *a, **kw):
        yield ""

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_engine_disposed(monkeypatch):
    dummy_engine = DummyEngine()
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    monkeypatch.setattr(server, "create_engine", lambda *a, **kw: dummy_engine)
    monkeypatch.setattr(server.SQLModel.metadata, "create_all", lambda *a, **k: None)

    app = server.create_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
    assert dummy_engine.disposed
