from typing import List, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn

from .plugins import Plugin, load_plugins
from .executor import LLMExecutor
from .config import Config, load_config


def create_app(
    plugin_names: Optional[List[str]] = None,
    config: Optional[Config] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> FastAPI:
    """Build the FastAPI application."""
    plugins = load_plugins(plugin_names)

    cfg = config or load_config()
    if model is not None:
        cfg.model = model
    if api_key is not None:
        cfg.api_key = api_key
    if api_base is not None:
        cfg.api_base = api_base

    executor = LLMExecutor(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)

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

    return app


def start_server(
    host: str = "0.0.0.0",
    port: int = 11434,
    plugin_names: Optional[List[str]] = None,
    config: Optional[Config] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> None:
    """Run the HTTP server."""
    cfg = config or load_config()
    if model is not None:
        cfg.model = model
    if api_key is not None:
        cfg.api_key = api_key
    if api_base is not None:
        cfg.api_base = api_base

    app = create_app(
        plugin_names=plugin_names,
        config=cfg,
    )
    uvicorn.run(app, host=host, port=port)
