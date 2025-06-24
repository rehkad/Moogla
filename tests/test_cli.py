from typer.testing import CliRunner
from fastapi.testclient import TestClient
from moogla.cli import app
from moogla import server
import types

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'serve' in result.output
    assert 'pull' in result.output

def test_pull():
    result = runner.invoke(app, ['pull', 'test-model'])
    assert result.exit_code == 0
    assert 'Pulling test-model ... done.' in result.output


def test_serve_with_plugin(monkeypatch):
    captured = {}

    def fake_run(app, host='0.0.0.0', port=11434):
        captured['app'] = app

    monkeypatch.setattr(server, 'uvicorn', types.SimpleNamespace(run=fake_run))

    result = runner.invoke(app, ['serve', '--plugin', 'tests.dummy_plugin'])
    assert result.exit_code == 0

    client = TestClient(captured['app'])
    resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 200
    assert resp.json()['choices'][0]['text'] == '!!CBA!!'
