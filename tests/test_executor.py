import types

import openai

from moogla.executor import LLMExecutor


class DummyClient:
    def __init__(self, content: str = "hi") -> None:
        self.content = content
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, model, messages, max_tokens):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=self.content))]
        )


class CountingClient(DummyClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def create(self, model, messages, max_tokens):
        self.calls += 1
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=messages[0]["content"]))]
        )


def test_complete(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(openai, "OpenAI", lambda api_key=None, base_url=None: dummy)
    executor = LLMExecutor(model="gpt-3.5-turbo")
    result = executor.complete("hello")
    assert result == "hi"


def test_cache_hit(monkeypatch):
    client = CountingClient()
    monkeypatch.setattr(openai, "OpenAI", lambda api_key=None, base_url=None: client)
    executor = LLMExecutor(model="gpt-3.5-turbo", cache_size=2)
    assert executor.complete("foo") == "foo"
    assert client.calls == 1
    # Second call should hit cache
    assert executor.complete("foo") == "foo"
    assert client.calls == 1


def test_cache_eviction(monkeypatch):
    client = CountingClient()
    monkeypatch.setattr(openai, "OpenAI", lambda api_key=None, base_url=None: client)
    executor = LLMExecutor(model="gpt-3.5-turbo", cache_size=1)
    executor.complete("a")
    executor.complete("b")
    assert client.calls == 2
    # "a" should be evicted from cache
    executor.complete("a")
    assert client.calls == 3
