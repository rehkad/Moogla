import httpx
import pytest
from fastapi.testclient import TestClient

import moogla.server as server
from moogla.server import create_app


class DummyExecutor:
    def complete(self, *a, **kw):
        return ""

    async def acomplete(self, *a, **kw):
        return ""

    async def astream(self, *a, **kw):
        yield ""


@pytest.mark.asyncio
async def test_metrics_endpoint(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(enable_metrics=True)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get("/health")
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


def test_metrics_disabled(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(enable_metrics=False)
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 404
