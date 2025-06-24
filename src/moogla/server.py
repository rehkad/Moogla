from typing import List, Optional

import os
import logging
import time

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn

from .plugins import Plugin, load_plugins
from .executor import LLMExecutor
from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
plugin_pre_timer = Histogram(
    "plugin_preprocess_seconds",
    "Time spent in plugin preprocess",
    ["plugin"],
)
plugin_post_timer = Histogram(
    "plugin_postprocess_seconds",
    "Time spent in plugin postprocess",
    ["plugin"],
)
plugin_errors = Counter(
    "plugin_errors_total",
    "Total plugin execution errors",
    ["plugin"],
)
request_timer = Histogram(
    "request_seconds",
    "HTTP request duration",
    ["path", "method"],
)


def create_app(
    plugin_names: Optional[List[str]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> FastAPI:
    """Build the FastAPI application."""
    plugins = load_plugins(plugin_names)

    model = model or os.getenv("MOOGLA_MODEL", "gpt-3.5-turbo")
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    api_base = api_base or os.getenv("OPENAI_API_BASE")

    executor = LLMExecutor(model=model, api_key=api_key, api_base=api_base)

    app = FastAPI(title="Moogla API")

    @app.middleware("http")
    async def log_and_time_requests(request: Request, call_next):
        start = time.perf_counter()
        logger.info("%s %s", request.method, request.url.path)
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception("Request failed")
            raise
        finally:
            duration = time.perf_counter() - start
            status = response.status_code if response else 500
            request_timer.labels(request.url.path, request.method).observe(duration)
            logger.info("%s %s %s %.3fs", request.method, request.url.path, status, duration)

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

    @app.get("/metrics")
    def metrics():
        """Expose Prometheus metrics."""
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    class Message(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        messages: List[Message]
        stream: bool = False

    class CompletionRequest(BaseModel):
        prompt: str
        stream: bool = False

    def apply_plugins(text: str) -> str:
        """Run text through plugin hooks and return the mock LLM output."""
        for plugin in plugins:
            start = time.perf_counter()
            try:
                text = plugin.run_preprocess(text)
            except Exception:
                plugin_errors.labels(plugin.module.__name__).inc()
                logger.exception("Preprocess failed in plugin %s", plugin.module.__name__)
                raise HTTPException(status_code=500, detail="Plugin preprocess failed")
            finally:
                plugin_pre_timer.labels(plugin.module.__name__).observe(time.perf_counter() - start)

        response = executor.complete(text)

        for plugin in plugins:
            start = time.perf_counter()
            try:
                response = plugin.run_postprocess(response)
            except Exception:
                plugin_errors.labels(plugin.module.__name__).inc()
                logger.exception("Postprocess failed in plugin %s", plugin.module.__name__)
                raise HTTPException(status_code=500, detail="Plugin postprocess failed")
            finally:
                plugin_post_timer.labels(plugin.module.__name__).observe(time.perf_counter() - start)

        return response

    @app.post("/v1/chat/completions")
    def chat_completions(req: ChatRequest):
        """Handle Chat API calls and return a reversed assistant reply."""
        if not req.messages:
            return {"choices": []}
        content = req.messages[-1].content
        reply = apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions")
    def completions(req: CompletionRequest):
        """Return a completion for the given prompt using the mock backend."""
        reply = apply_plugins(req.prompt)
        return {"choices": [{"text": reply}]}

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
