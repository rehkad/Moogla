from typer.testing import CliRunner
import httpx
from fastapi.testclient import TestClient

from moogla.cli import app
from moogla import server, plugins_config

runner = CliRunner()


def test_cli_plugin_management(tmp_path, monkeypatch):
    db = tmp_path / "plugins.db"
    monkeypatch.setenv("MOOGLA_PLUGIN_DB", str(db))

    result = runner.invoke(app, ["plugin", "add", "tests.dummy_plugin"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["plugin", "list"])
    assert result.exit_code == 0
    assert "tests.dummy_plugin" in result.output

    result = runner.invoke(app, ["plugin", "remove", "tests.dummy_plugin"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["plugin", "list"])
    assert "tests.dummy_plugin" not in result.output


class DummyExecutor:
    async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
        return prompt[::-1]


def test_persisted_plugins_loaded(tmp_path, monkeypatch):
    db = tmp_path / "plugins.db"
    monkeypatch.setenv("MOOGLA_PLUGIN_DB", str(db))
    plugins_config.add_plugin("tests.dummy_plugin")

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app_instance = server.create_app()
    client = TestClient(app_instance)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "!!CBA!!"
