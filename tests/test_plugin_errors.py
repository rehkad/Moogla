import pytest
from moogla.server import create_app
from fastapi.testclient import TestClient
import sys
import types


def test_invalid_plugin_raises_import_error():
    with pytest.raises(ImportError):
        create_app(["nonexistent.module"])


def test_preprocess_exception_results_in_500():
    mod = types.ModuleType('error_pre_plugin')

    def preprocess(text: str) -> str:
        raise RuntimeError('fail')

    mod.preprocess = preprocess
    sys.modules['error_pre_plugin'] = mod
    app = create_app(['error_pre_plugin'])
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 500
    sys.modules.pop('error_pre_plugin', None)


def test_postprocess_exception_results_in_500():
    mod = types.ModuleType('error_post_plugin')

    def postprocess(text: str) -> str:
        raise RuntimeError('boom')

    mod.postprocess = postprocess
    sys.modules['error_post_plugin'] = mod
    app = create_app(['error_post_plugin'])
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 500
    sys.modules.pop('error_post_plugin', None)
