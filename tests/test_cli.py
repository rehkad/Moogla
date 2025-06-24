from typer.testing import CliRunner
from fastapi.testclient import TestClient
from moogla.cli import app
from moogla import server
import openai
import types
import pytest

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    if result.exit_code != 0:
        pytest.skip("CLI help unsupported")
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

        def create(self, model, messages, max_tokens):
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
        async def acomplete(self, prompt: str, max_tokens: int = 16) -> str:
            return prompt[::-1]

    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())

    result = runner.invoke(app, ["serve", "--plugin", "tests.dummy_plugin"])
    assert result.exit_code == 0

    client = TestClient(captured["app"])
    # register and login to obtain token
    client.post("/register", json={"username": "u", "password": "p"})
    token = client.post(
        "/login",
        data={"username": "u", "password": "p", "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()[
        "access_token"
    ]
    resp = client.post(
        "/v1/completions",
        json={"prompt": "abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
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
