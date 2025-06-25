import importlib
import os
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from moogla import plugins_config, server
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


def test_async_setup_called(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.async_setup_plugin", suffix="##")

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()

    async_setup_plugin = importlib.import_module("tests.async_setup_plugin")
    assert async_setup_plugin.configured == {"suffix": "##"}

    client = TestClient(app)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "cba##"
    plugins_config.set_plugin_file(None)


@pytest.mark.asyncio
async def test_async_setup_inside_running_loop(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.async_setup_plugin", suffix="@@")

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app()

    async_setup_plugin = importlib.import_module("tests.async_setup_plugin")
    await asyncio.sleep(0.01)
    assert async_setup_plugin.configured == {"suffix": "@@"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "cba@@"
    plugins_config.set_plugin_file(None)
