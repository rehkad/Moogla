import os
import pytest
from moogla.server import create_app
from fastapi.testclient import TestClient
import sys
import types

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_invalid_plugin_raises_import_error():
    with pytest.raises(ImportError):
        create_app(["nonexistent.module"])


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


def test_preprocess_exception_results_in_500(tmp_path, monkeypatch):
    mod = types.ModuleType('error_pre_plugin')

    def preprocess(text: str) -> str:
        raise RuntimeError('fail')

    mod.preprocess = preprocess
    sys.modules['error_pre_plugin'] = mod
    monkeypatch.setattr("moogla.server.LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(['error_pre_plugin'], db_url=f"sqlite:///{tmp_path}/db.db")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Plugin error"
    sys.modules.pop('error_pre_plugin', None)


def test_postprocess_exception_results_in_500(tmp_path, monkeypatch):
    mod = types.ModuleType('error_post_plugin')

    def postprocess(text: str) -> str:
        raise RuntimeError('boom')

    mod.postprocess = postprocess
    sys.modules['error_post_plugin'] = mod
    monkeypatch.setattr("moogla.server.LLMExecutor", lambda *a, **kw: DummyExecutor())
    app = create_app(['error_post_plugin'], db_url=f"sqlite:///{tmp_path}/db.db")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Plugin error"
    sys.modules.pop('error_post_plugin', None)
