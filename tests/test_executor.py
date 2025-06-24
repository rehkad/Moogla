import types

import openai
import pytest

from moogla.executor import LLMExecutor


class DummyClient:
    def __init__(self, content: str = "hi") -> None:
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


def test_complete(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(openai, "OpenAI", lambda api_key=None, base_url=None: dummy)
    monkeypatch.setattr(
        openai, "AsyncOpenAI", lambda api_key=None, base_url=None: dummy
    )
    executor = LLMExecutor(model="gpt-3.5-turbo")
    result = executor.complete("hello")
    assert result == "hi"


def test_hf_backend(monkeypatch):
    import sys

    class DummyPipeline:
        def __call__(self, text, max_new_tokens=16):
            return [{"generated_text": text[::-1]}]

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(pipeline=lambda *a, **k: DummyPipeline()),
    )

    executor = LLMExecutor(model="some/model")
    result = executor.complete("abc")
    assert result == "cba"


@pytest.mark.asyncio
async def test_astream(monkeypatch):
    class DummyStream:
        def __init__(self, text):
            self.text = text

        def __iter__(self):
            for ch in self.text:
                yield types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(delta=types.SimpleNamespace(content=ch))
                    ]
                )

    class DummyAsyncStream:
        def __init__(self, text):
            self.text = text

        def __aiter__(self):
            self._iter = iter(self.text)
            return self

        async def __anext__(self):
            try:
                ch = next(self._iter)
            except StopIteration:
                raise StopAsyncIteration
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content=ch))]
            )

    class StreamClient(DummyClient):
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
            if stream:
                return DummyStream(self.content)
            return super().create(
                model,
                messages,
                max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=stream,
            )

    class AsyncStreamClient(StreamClient):
        async def create(
            self,
            model,
            messages,
            max_tokens,
            *,
            temperature=None,
            top_p=None,
            stream=False,
        ):
            if stream:
                return DummyAsyncStream(self.content)
            return super().create(
                model,
                messages,
                max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=stream,
            )

    dummy = StreamClient("hi")
    adummy = AsyncStreamClient("hi")
    monkeypatch.setattr(openai, "OpenAI", lambda api_key=None, base_url=None: dummy)
    monkeypatch.setattr(
        openai, "AsyncOpenAI", lambda api_key=None, base_url=None: adummy
    )
    executor = LLMExecutor(model="gpt-3.5-turbo")
    tokens = [t async for t in executor.astream("hello")]
    assert tokens == list("hi")
