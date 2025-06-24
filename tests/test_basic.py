import types
import openai
from fastapi.testclient import TestClient
from moogla.server import create_app


class DummyAsyncChat:
    async def create(self, model, messages=None, prompt=None, stream=False):
        text = messages[-1]["content"] if messages else prompt
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text))]
        )


class DummyAsyncOpenAI:
    def __init__(self):
        self.chat = types.SimpleNamespace(completions=DummyAsyncChat())
        self.completions = DummyAsyncChat()


def test_health_check(monkeypatch):
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda: DummyAsyncOpenAI())
    client = TestClient(create_app(openai_client=DummyAsyncOpenAI()))
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}
