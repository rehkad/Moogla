import httpx
import pytest
from prometheus_client.parser import text_string_to_metric_families

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
async def test_metrics_endpoint(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(server_api_key="secret")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/v1/completions",
            json={"prompt": "abc"},
            headers={"X-API-Key": "secret"},
        )
        resp = await client.get("/metrics", headers={"X-API-Key": "secret"})
    assert resp.status_code == 200
    metrics = {f.name: f for f in text_string_to_metric_families(resp.text)}
    req = next(
        s for s in metrics["moogla_requests"].samples if s.name == "moogla_requests_total" and s.labels["path"] == "/v1/completions"
    )
    assert req.value >= 1
    assert metrics["moogla_tokens_generated"].samples[0].value >= 1


@pytest.mark.asyncio
async def test_metrics_requires_auth(monkeypatch):
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(server_api_key="secret")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 401
