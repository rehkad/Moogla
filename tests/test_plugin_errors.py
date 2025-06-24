import pytest
import openai
import types
from moogla.server import create_app


class DummyAsyncChat:
    async def create(self, model, messages=None, prompt=None, stream=False):
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=""))])


class DummyAsyncOpenAI:
    def __init__(self):
        self.chat = types.SimpleNamespace(completions=DummyAsyncChat())
        self.completions = DummyAsyncChat()


def test_invalid_plugin_raises_import_error():
    with pytest.raises(ImportError):
        create_app(["nonexistent.module"], openai_client=DummyAsyncOpenAI())
