import json
import logging
import os
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .executor import LLMExecutor
from .plugins import load_plugins

logger = logging.getLogger(__name__)


def create_app(
    plugin_names: Optional[List[str]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    server_api_key: Optional[str] = None,
    rate_limit: Optional[int] = None,
    redis_url: Optional[str] = None,
    db_url: Optional[str] = None,
) -> FastAPI:
    """Build the FastAPI application."""
    plugins = load_plugins(plugin_names)

    model = model or os.getenv("MOOGLA_MODEL", "gpt-3.5-turbo")
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    api_base = api_base or os.getenv("OPENAI_API_BASE")
    server_api_key = server_api_key or os.getenv("MOOGLA_API_KEY")
    if rate_limit is None:
        env_limit = os.getenv("MOOGLA_RATE_LIMIT")
        rate_limit = int(env_limit) if env_limit else None
    redis_url = redis_url or os.getenv("MOOGLA_REDIS_URL", "redis://localhost:6379")

    executor = LLMExecutor(model=model, api_key=api_key, api_base=api_base)

    dependencies = []

    if server_api_key:

        async def verify_api_key(
            x_api_key: Optional[str] = Header(None, alias="X-API-Key")
        ) -> None:
            if x_api_key != server_api_key:
                raise HTTPException(status_code=401, detail="Invalid API Key")

        dependencies.append(Depends(verify_api_key))

    if rate_limit:
        dependencies.append(Depends(RateLimiter(times=rate_limit, seconds=60)))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        import redis.asyncio as redis

        redis_conn = redis.from_url(redis_url, encoding="utf8", decode_responses=True)
        await FastAPILimiter.init(redis_conn)
        yield
        await FastAPILimiter.close()

    app = FastAPI(title="Moogla API", dependencies=dependencies, lifespan=lifespan)
    app.state.db_url = db_url

    static_dir = Path(__file__).resolve().parent / "web"
    if static_dir.exists():
        app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")

        @app.get("/")
        def root():
            """Serve the bundled web UI index page."""
            index_path = static_dir / "index.html"
            return FileResponse(index_path)

    @app.get("/health")
    def health_check():
        """Return a simple heartbeat response for monitoring."""
        return {"status": "ok"}

    class Message(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        messages: List[Message]
        stream: bool = False

    class CompletionRequest(BaseModel):
        prompt: str
        stream: bool = False

    async def apply_plugins(text: str) -> str:
        """Run text through plugin hooks and return the mock LLM output."""
        for plugin in plugins:
            try:
                text = await plugin.run_preprocess(text)
            except Exception as exc:
                logger.exception("Preprocess plugin failed: %s", exc)
                raise HTTPException(status_code=500, detail="Plugin error") from exc
        response = await executor.acomplete(text)
        for plugin in plugins:
            try:
                response = await plugin.run_postprocess(response)
            except Exception as exc:
                logger.exception("Postprocess plugin failed: %s", exc)
                raise HTTPException(status_code=500, detail="Plugin error") from exc
        return response

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest):
        """Handle Chat API calls and return a reversed assistant reply."""
        if not req.messages:
            return {"choices": []}
        content = req.messages[-1].content
        if req.stream:
            async def event_stream():
                reply = await apply_plugins(content)
                for char in reply:
                    yield json.dumps({"choices": [{"delta": {"content": char}}]}) + "\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        reply = await apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions")
    async def completions(req: CompletionRequest):
        """Return a completion for the given prompt using the mock backend."""
        if req.stream:
            async def event_stream():
                reply = await apply_plugins(req.prompt)
                for char in reply:
                    yield json.dumps({"choices": [{"delta": {"content": char}}]}) + "\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        reply = await apply_plugins(req.prompt)
        return {"choices": [{"text": reply}]}

    return app


def start_server(
    host: str = "0.0.0.0",
    port: int = 11434,
    plugin_names: Optional[List[str]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    server_api_key: Optional[str] = None,
    rate_limit: Optional[int] = None,
    redis_url: Optional[str] = None,
    db_url: Optional[str] = None,
) -> None:
    """Run the HTTP server."""
    app = create_app(
        plugin_names=plugin_names,
        model=model,
        api_key=api_key,
        api_base=api_base,
        server_api_key=server_api_key,
        rate_limit=rate_limit,
        redis_url=redis_url,
        db_url=db_url,
    )
    uvicorn.run(app, host=host, port=port)
