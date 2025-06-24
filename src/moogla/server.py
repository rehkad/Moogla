from typing import List, Optional

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn
import json

from .plugins import Plugin, load_plugins
from .executor import LLMExecutor


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
) -> None:
    """Run the HTTP server."""
    app = create_app(
        plugin_names=plugin_names,
        model=model,
        api_key=api_key,
        api_base=api_base,
    )
    uvicorn.run(app, host=host, port=port)
