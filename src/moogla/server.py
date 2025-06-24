from typing import List, Optional

import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn
import logging

from .plugins import Plugin, load_plugins
from .executor import LLMExecutor

logger = logging.getLogger(__name__)


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
        reply = await apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions")
    async def completions(req: CompletionRequest):
        """Return a completion for the given prompt using the mock backend."""
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
) -> None:
    """Run the HTTP server."""
    app = create_app(
        plugin_names=plugin_names,
        model=model,
        api_key=api_key,
        api_base=api_base,
    )
    uvicorn.run(app, host=host, port=port)
