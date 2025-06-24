import os
from fastapi.testclient import TestClient
from importlib import metadata
from moogla import server
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")

class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

def test_entrypoint_plugin_loaded(monkeypatch):
    ep = metadata.EntryPoint(
        name="dummy", value="tests.dummy_plugin", group="moogla.plugins"
    )

    def fake_entry_points(*, group=None):
        if group == "moogla.plugins":
            return metadata.EntryPoints((ep,))
        return metadata.EntryPoints(())

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())

    app = create_app()
    client = TestClient(app)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "!!CBA!!"
