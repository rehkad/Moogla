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


def test_complete(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(openai, "OpenAI", lambda api_key=None, base_url=None: dummy)
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda api_key=None, base_url=None: dummy)
    executor = LLMExecutor(model="gpt-3.5-turbo")
    result = executor.complete("hello")
    assert result == "hi"
