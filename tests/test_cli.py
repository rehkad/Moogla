from typer.testing import CliRunner
from fastapi.testclient import TestClient
from moogla.cli import app
from moogla import server
import openai
import types

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'serve' in result.output
    assert 'pull' in result.output

def test_pull(tmp_path):
    src = tmp_path / "model.bin"
    src.write_text("data")
    dest_dir = tmp_path / "models"
    result = runner.invoke(app, ["pull", str(src), "--dir", str(dest_dir)])
    assert result.exit_code == 0
    dest = dest_dir / "model.bin"
    assert dest.exists()
    assert dest.read_text() == "data"


def test_serve_with_plugin(monkeypatch):
    captured = {}

    def fake_run(app, host='0.0.0.0', port=11434):
        captured['app'] = app

    class DummyClient:
        def __init__(self, content: str = "HI") -> None:
            self.content = content
            self.chat = types.SimpleNamespace(completions=self)

        def create(self, model, messages, max_tokens):
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=self.content))]
            )

    monkeypatch.setattr(server, 'uvicorn', types.SimpleNamespace(run=fake_run))
    monkeypatch.setattr(openai, 'OpenAI', lambda api_key=None, base_url=None: DummyClient("CBA"))

    class DummyExecutor:
        async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
            return prompt[::-1]

    monkeypatch.setattr(server, 'LLMExecutor', lambda *a, **kw: DummyExecutor())

    result = runner.invoke(app, ['serve', '--plugin', 'tests.dummy_plugin'])
    assert result.exit_code == 0

    client = TestClient(captured['app'])
    resp = client.post('/v1/completions', json={'prompt': 'abc'})
    assert resp.status_code == 200
    assert resp.json()['choices'][0]['text'] == '!!CBA!!'
