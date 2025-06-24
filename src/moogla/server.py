from typing import List, Optional

import os
import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn

from . import configure_logging
from .plugins import Plugin, load_plugins
from .executor import LLMExecutor

try:  # pragma: no-cover - optional dependency
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    REQUEST_COUNT = Counter(
        "requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "request_latency_seconds",
        "HTTP request latency",
        ["endpoint"],
    )
    HAVE_METRICS = True
except Exception:  # pragma: no-cover - optional dependency may be missing
    HAVE_METRICS = False


def create_app(
    plugin_names: Optional[List[str]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> FastAPI:
    """Build the FastAPI application."""
    configure_logging()
    logger = logging.getLogger(__name__)

    plugins = load_plugins(plugin_names)

    model = model or os.getenv("MOOGLA_MODEL", "gpt-3.5-turbo")
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    api_base = api_base or os.getenv("OPENAI_API_BASE")

    executor = LLMExecutor(model=model, api_key=api_key, api_base=api_base)

    app = FastAPI(title="Moogla API")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        logger.info("%s %s", request.method, request.url.path)
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s -> %s (%.3fs)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        if HAVE_METRICS:
            endpoint = request.url.path
            REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
            REQUEST_LATENCY.labels(endpoint).observe(duration)
        return response

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
            text = await plugin.run_preprocess(text)
        response = await executor.acomplete(text)
        for plugin in plugins:
            response = await plugin.run_postprocess(response)
        return response

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest):
        """Handle Chat API calls and return a reversed assistant reply."""
        if not req.messages:
            return {"choices": []}
        content = req.messages[-1].content
        reply = await apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions")
    async def completions(req: CompletionRequest):
        """Return a completion for the given prompt using the mock backend."""
        reply = await apply_plugins(req.prompt)
        return {"choices": [{"text": reply}]}

    if HAVE_METRICS:
        @app.get("/metrics")
        def metrics() -> Response:
            """Expose Prometheus metrics."""
            data = generate_latest()
            return Response(data, media_type=CONTENT_TYPE_LATEST)

    return app


def start_server(
    host: str = "0.0.0.0",
    port: int = 11434,
    plugin_names: Optional[List[str]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> None:
    """Run the HTTP server."""
    app = create_app(
        plugin_names=plugin_names,
        model=model,
        api_key=api_key,
        api_base=api_base,
    )
    uvicorn.run(app, host=host, port=port)
