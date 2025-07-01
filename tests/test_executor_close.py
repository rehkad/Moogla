import types

import openai
import pytest

from moogla.executor import LLMExecutor


class DummyClient:
    def __init__(self) -> None:
        self.closed = False
        self.chat = types.SimpleNamespace(completions=self)

    def close(self) -> None:
        self.closed = True

    def create(self, *a, **k):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content=None))]
        )


@pytest.mark.asyncio
async def test_context_manager_closes(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(openai, "OpenAI", lambda *a, **k: dummy)
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda *a, **k: dummy)

    async with LLMExecutor(model="gpt-3.5-turbo"):
        pass

    assert dummy.closed


def test_sync_context_manager(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(openai, "OpenAI", lambda *a, **k: dummy)
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda *a, **k: dummy)

    with LLMExecutor(model="gpt-3.5-turbo"):
        pass

    assert dummy.closed
