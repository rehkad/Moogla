import asyncio
import sys
import types

import pytest

from moogla.executor import LLMExecutor


class DummyAsyncLlama:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path

    async def __call__(self, prompt: str, max_tokens: int = 16, stream: bool = False):
        if stream:

            async def gen():
                for ch in prompt[::-1]:
                    yield {"choices": [{"text": ch}]}

            return gen()
        return {"choices": [{"text": prompt[::-1]}]}


@pytest.mark.asyncio
async def test_async_llama_usage(monkeypatch):
    dummy_module = types.SimpleNamespace(
        AsyncLlama=DummyAsyncLlama, Llama=DummyAsyncLlama
    )
    monkeypatch.setitem(sys.modules, "llama_cpp", dummy_module)

    called = False

    async def fake_to_thread(func, *args, **kwargs):
        nonlocal called
        called = True
        return await func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    executor = LLMExecutor(model="some/model.gguf")

    result = await executor.acomplete("abc")
    assert result == "cba"
    assert called is False

    tokens = [t async for t in executor.astream("abc")]
    assert tokens == list("cba")
    assert called is False
