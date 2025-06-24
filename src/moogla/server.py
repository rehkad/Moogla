from typing import List, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from importlib import resources
from pydantic import BaseModel
import uvicorn

from .plugins import Plugin, load_plugins


def create_app(plugin_names: Optional[List[str]] = None) -> FastAPI:
    """Build the FastAPI application."""
    plugins = load_plugins(plugin_names)

    app = FastAPI(title="Moogla API")

    try:
        with resources.as_file(resources.files("moogla").joinpath("web")) as static_dir:
            if static_dir.is_dir():
                app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")
    except FileNotFoundError:
        pass

    @app.get("/health")
    def health_check():
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

    def apply_plugins(text: str) -> str:
        for plugin in plugins:
            text = plugin.run_preprocess(text)
        response = text[::-1]  # mock generation
        for plugin in plugins:
            response = plugin.run_postprocess(response)
        return response

    @app.post("/v1/chat/completions")
    def chat_completions(req: ChatRequest):
        if not req.messages:
            return {"choices": []}
        content = req.messages[-1].content
        reply = apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions")
    def completions(req: CompletionRequest):
        reply = apply_plugins(req.prompt)
        return {"choices": [{"text": reply}]}

    return app


def start_server(host: str = "0.0.0.0", port: int = 11434, plugin_names: Optional[List[str]] = None) -> None:
    """Run the HTTP server."""
    app = create_app(plugin_names)
    uvicorn.run(app, host=host, port=port)
