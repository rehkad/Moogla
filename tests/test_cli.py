import types

import openai
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from moogla import server
from moogla.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.output
    assert "pull" in result.output


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
            result = runner.invoke(app, ["pull", str(src), "--dir", target_dir])
            assert result.exit_code == 0
            assert (Path(target_dir) / "dummy.txt").exists()


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
        app, ["pull", "http://example.com/x.bin", "--dir", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert not (tmp_path / "x.bin").exists()
    assert "Failed to download" in result.output
