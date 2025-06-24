import os
import pytest
import logging
from moogla.server import create_app
from fastapi.testclient import TestClient
import sys
import types
from moogla import server


class DummyExecutor:
    def complete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_invalid_plugin_raises_import_error():
    with pytest.raises(ImportError):
        create_app(["nonexistent.module"])


def test_preprocess_exception_results_in_500(monkeypatch, caplog):
    mod = types.ModuleType('error_pre_plugin')

    def preprocess(text: str) -> str:
        raise RuntimeError('fail')

    mod.preprocess = preprocess
    sys.modules['error_pre_plugin'] = mod
    monkeypatch.setattr(server, 'LLMExecutor', lambda *a, **kw: DummyExecutor())
    app = create_app(['error_pre_plugin'])
    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 500
    assert any('Preprocess failed' in r.message for r in caplog.records)
    sys.modules.pop('error_pre_plugin', None)


def test_postprocess_exception_results_in_500(monkeypatch, caplog):
    mod = types.ModuleType('error_post_plugin')

    def postprocess(text: str) -> str:
        raise RuntimeError('boom')

    mod.postprocess = postprocess
    sys.modules['error_post_plugin'] = mod
    monkeypatch.setattr(server, 'LLMExecutor', lambda *a, **kw: DummyExecutor())
    app = create_app(['error_post_plugin'])
    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 500
    assert any('Postprocess failed' in r.message for r in caplog.records)
    sys.modules.pop('error_post_plugin', None)
