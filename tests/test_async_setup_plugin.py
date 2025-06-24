import os
import importlib
from fastapi.testclient import TestClient
import pytest

from moogla import server, plugins_config
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int | None = None, temperature: float | None = None, top_p: float | None = None) -> str:
        return prompt[::-1]

    async def acomplete(self, prompt: str, max_tokens: int | None = None, temperature: float | None = None, top_p: float | None = None) -> str:
        return prompt[::-1]

    async def astream(self, prompt: str, max_tokens: int | None = None, temperature: float | None = None, top_p: float | None = None):
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
