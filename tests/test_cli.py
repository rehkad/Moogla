import types

import httpx
import openai
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from moogla import plugins_config, server
from moogla.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.output
    assert "pull" in result.output
    assert "models" in result.output


def test_serve_with_plugin(monkeypatch):
    captured = {}

    def fake_run(app, host="0.0.0.0", port=11434):
        captured["app"] = app

    class DummyClient:
        def __init__(self, content: str = "HI") -> None:
            self.content = content
            self.chat = types.SimpleNamespace(completions=self)

        def create(
            self,
            model,
            messages,
            max_tokens,
            *,
            temperature=None,
            top_p=None,
            stream=False,
        ):
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content=self.content)
                    )
                ]
            )

    monkeypatch.setattr(server, "uvicorn", types.SimpleNamespace(run=fake_run))
    monkeypatch.setattr(
        openai, "OpenAI", lambda api_key=None, base_url=None: DummyClient("CBA")
    )

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

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())

    result = runner.invoke(app, ["serve", "--plugin", "tests.dummy_plugin"])
    assert result.exit_code == 0

    client = TestClient(captured["app"])
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "!!CBA!!"


def test_pull_downloads_to_custom_dir():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as source_dir:
        src = Path(source_dir) / "dummy.txt"
        src.write_text("hi")

        with tempfile.TemporaryDirectory() as target_dir:
            result = runner.invoke(app, ["pull", str(src), "--directory", target_dir])
            assert result.exit_code == 0
            assert (Path(target_dir) / "dummy.txt").exists()


def test_pull_http_download(monkeypatch, tmp_path):
    import contextlib

    import httpx

    data = b"hello"

    def fake_stream(method, url, *a, **kw):
        @contextlib.contextmanager
        def cm():
            class FakeResp:
                headers = {"content-length": str(len(data))}

                def raise_for_status(self):
                    pass

                def iter_bytes(self):
                    yield from [data[:2], data[2:]]

            yield FakeResp()

        return cm()

    monkeypatch.setattr(httpx, "stream", fake_stream)

    result = runner.invoke(
        app, ["pull", "http://example.com/x.bin", "--directory", str(tmp_path)]
    )
    assert result.exit_code == 0
    out_file = tmp_path / "x.bin"
    assert out_file.exists()
    assert out_file.read_bytes() == data


def test_pull_http_error(monkeypatch, tmp_path):
    import contextlib

    import httpx

    def fake_stream(method, url, *a, **kw):
        @contextlib.contextmanager
        def cm():
            class FakeResp:
                headers = {}

                def raise_for_status(self):
                    raise httpx.HTTPStatusError("boom", request=None, response=None)

                def iter_bytes(self):
                    return iter([])

            yield FakeResp()

        return cm()

    monkeypatch.setattr(httpx, "stream", fake_stream)

    result = runner.invoke(
        app, ["pull", "http://example.com/x.bin", "--directory", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert not (tmp_path / "x.bin").exists()
    assert "Failed to download" in result.output


def test_models_lists_files(tmp_path, monkeypatch):
    models_dir = tmp_path / ".cache" / "moogla" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "a.bin").write_text("hi")
    (models_dir / "b.gguf").write_text("ok")

    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "a.bin" in result.output
    assert "b.gguf" in result.output


def test_remove_model(tmp_path, monkeypatch):
    models_dir = tmp_path / ".cache" / "moogla" / "models"
    models_dir.mkdir(parents=True)
    path = models_dir / "a.bin"
    path.write_text("hi")

    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["remove", "a.bin"], input="y\n")
    assert result.exit_code == 0
    assert not path.exists()


def test_remove_model_yes_flag(tmp_path, monkeypatch):
    models_dir = tmp_path / ".cache" / "moogla" / "models"
    models_dir.mkdir(parents=True)
    path = models_dir / "b.bin"
    path.write_text("hi")

    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["remove", "b.bin", "--yes"])
    assert result.exit_code == 0
    assert not path.exists()


def test_remove_model_missing(tmp_path, monkeypatch):
    models_dir = tmp_path / ".cache" / "moogla" / "models"
    models_dir.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["remove", "c.bin", "--yes"])
    assert result.exit_code == 1
    assert "Model not found" in result.output


def test_plugin_show_command(tmp_path, monkeypatch):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.dummy_plugin", flag="yes", number="1")

    result = runner.invoke(app, ["plugin", "show", "tests.dummy_plugin"])
    assert result.exit_code == 0
    assert "flag=yes" in result.output
    assert "number=1" in result.output


def test_reload_plugins_command(monkeypatch, tmp_path):
    cfg = tmp_path / "plugins.yaml"
    monkeypatch.setenv("MOOGLA_PLUGIN_FILE", str(cfg))
    plugins_config.add_plugin("tests.dummy_plugin")

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

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    app_instance = server.create_app()
    client = TestClient(app_instance)

    plugins_config.remove_plugin("tests.dummy_plugin")
    plugins_config.add_plugin("tests.setup_plugin", suffix="!!")

    def fake_post(url, *a, **kw):
        assert url.endswith("/reload-plugins")
        resp = client.post("/reload-plugins")
        return types.SimpleNamespace(
            status_code=resp.status_code,
            json=resp.json,
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = runner.invoke(app, ["reload-plugins"])
    assert result.exit_code == 0
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.json()["choices"][0]["text"] == "cba!!"
