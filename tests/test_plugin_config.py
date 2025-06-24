from typer.testing import CliRunner
import httpx
from fastapi.testclient import TestClient
import pytest

from moogla.cli import app
from moogla import server, plugins_config

runner = CliRunner()


def test_cli_plugin_management(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))

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


def test_persisted_plugins_loaded(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.dummy_plugin")

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app_instance = server.create_app()
    client = TestClient(app_instance)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "!!CBA!!"


def test_add_invalid_plugin_direct(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    with pytest.raises(ImportError):
        plugins_config.add_plugin("no.such.module")
    assert not cfg.exists()


def test_cli_add_invalid_plugin(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))

    result = runner.invoke(app, ["plugin", "add", "no.such.module"])
    assert result.exit_code == 1
    assert "Failed to import plugin" in result.output
    assert not cfg.exists()
