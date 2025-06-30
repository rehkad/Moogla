from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from moogla import plugins_config, server
from moogla.cli import app

runner = CliRunner()


def test_cli_plugin_management(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))

    result = runner.invoke(
        app,
        [
            "plugin",
            "add",
            "tests.dummy_plugin",
            "--set",
            "flag=yes",
            "--set",
            "number=1",
        ],
    )
    assert result.exit_code == 0

    settings = plugins_config.get_plugin_settings("tests.dummy_plugin")
    assert settings == {"flag": "yes", "number": "1"}

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


def test_plugin_settings_used(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.setup_plugin", suffix="??")

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app_instance = server.create_app()

    import importlib

    setup_plugin = importlib.import_module("tests.setup_plugin")
    assert setup_plugin.configured == {"suffix": "??"}

    client = TestClient(app_instance)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "cba??"


def test_corrupted_file_raises_runtime_error(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    cfg.write_text("plugins: [")
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))

    with pytest.raises(RuntimeError):
        plugins_config.get_plugins()


def test_permission_error_raises_runtime_error(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    cfg.write_text("plugins: []")
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))

    real_open = open

    def fake_open(path, mode="r", *args, **kwargs):
        if Path(path) == cfg and "r" in mode:
            raise PermissionError("no permission")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    with pytest.raises(RuntimeError):
        plugins_config.get_plugins()


def test_cli_plugin_clear(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.dummy_plugin")
    result = runner.invoke(app, ["plugin", "clear"])
    assert result.exit_code == 0
    assert "Cleared" in result.output
    assert plugins_config.get_plugins() == []
