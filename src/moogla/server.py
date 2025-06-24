from typing import List, Optional, AsyncIterable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn

import openai

from .plugins import Plugin, load_plugins


def create_app(
    plugin_names: Optional[List[str]] = None,
    openai_client: Optional[openai.AsyncOpenAI] = None,
) -> FastAPI:
    """Build the FastAPI application."""
    plugins = load_plugins(plugin_names)
    openai_client = openai_client or openai.AsyncOpenAI()

    app = FastAPI(title="Moogla API")

    static_dir = Path(__file__).resolve().parent / "web"
    if static_dir.exists():
        app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")

        @app.get("/")
        def root():
            index_path = static_dir / "index.html"
            return FileResponse(index_path)

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

    async def apply_plugins(text: str) -> str:
        for plugin in plugins:
            text = plugin.run_preprocess(text)
        resp = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}],
        )
        response = resp.choices[0].message.content
        for plugin in plugins:
            response = plugin.run_postprocess(response)
        return response

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest):
        if not req.messages:
            return {"choices": []}
        content = req.messages[-1].content
        if req.stream:
            async def generator() -> AsyncIterable[str]:
                async for chunk in await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": content}],
                    stream=True,
                ):
                    yield chunk.choices[0].delta.content or ""

            return StreamingResponse(generator(), media_type="text/plain")

        reply = await apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions")
    async def completions(req: CompletionRequest):
        if req.stream:
            async def generator() -> AsyncIterable[str]:
                async for chunk in await openai_client.completions.create(
                    model="gpt-3.5-turbo",
                    prompt=req.prompt,
                    stream=True,
                ):
                    yield chunk.choices[0].text

            return StreamingResponse(generator(), media_type="text/plain")

        reply = await apply_plugins(req.prompt)
        return {"choices": [{"text": reply}]}

    return app


def start_server(host: str = "0.0.0.0", port: int = 11434, plugin_names: Optional[List[str]] = None) -> None:
    """Run the HTTP server."""
    app = create_app(plugin_names)
    uvicorn.run(app, host=host, port=port)
