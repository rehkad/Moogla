import pytest

import moogla.server as server
from moogla.server import create_app


class DummyExecutor:
    def complete(self, *a, **kw):
        return ""

    async def acomplete(self, *a, **kw):
        return ""

    async def astream(self, *a, **kw):
        yield ""

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_missing_jwt_secret(monkeypatch):
    monkeypatch.delenv("MOOGLA_JWT_SECRET", raising=False)
    monkeypatch.setattr(server, "LLMExecutor", lambda *a, **kw: DummyExecutor())
    with pytest.raises(RuntimeError):
        create_app(server_api_key="secret")
