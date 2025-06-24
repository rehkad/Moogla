import types
import openai
from fastapi.testclient import TestClient

from moogla.server import create_app


class DummyAsyncChat:
    async def create(self, model, messages=None, prompt=None, stream=False):
        text = messages[-1]["content"] if messages else prompt
        reversed_text = text[::-1]
        if stream:
            async def gen():
                for ch in reversed_text:
                    yield types.SimpleNamespace(
                        choices=[types.SimpleNamespace(
                            delta=types.SimpleNamespace(content=ch),
                            text=ch,
                        )]
                    )
            return gen()
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content=reversed_text),
                    text=reversed_text,
                )
            ]
        )


class DummyAsyncOpenAI:
    def __init__(self):
        self.chat = types.SimpleNamespace(completions=DummyAsyncChat())
        self.completions = DummyAsyncChat()


def test_chat_completion(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    app = create_app(openai_client=DummyAsyncOpenAI())
    client = TestClient(app)
    resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "olleh"


def test_completion_endpoint(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    app = create_app(openai_client=DummyAsyncOpenAI())
    client = TestClient(app)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "cba"


def test_plugins(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    app = create_app(["tests.dummy_plugin"], openai_client=DummyAsyncOpenAI())
    client = TestClient(app)
    resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "!!OLLEH!!"


def test_root_endpoint(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    app = create_app(openai_client=DummyAsyncOpenAI())
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Moogla Chat" in resp.text


def test_streaming_chat(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    app = create_app(openai_client=DummyAsyncOpenAI())
    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
    )
    assert resp.status_code == 200
    assert resp.text == "ih"


def test_streaming_completion(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    app = create_app(openai_client=DummyAsyncOpenAI())
    client = TestClient(app)
    resp = client.post(
        "/v1/completions",
        json={"prompt": "abc", "stream": True},
    )
    assert resp.status_code == 200
    assert resp.text == "cba"
