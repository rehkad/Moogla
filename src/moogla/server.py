import json
import logging
import os
import time
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .executor import LLMExecutor
from .plugins import load_plugins
from . import auth

logger = logging.getLogger(__name__)


def create_app(
    plugin_names: Optional[List[str]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    server_api_key: Optional[str] = None,
    rate_limit: Optional[int] = None,
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

    executor = LLMExecutor(model=model, api_key=api_key, api_base=api_base)

    auth.init(db_url or "sqlite:///./users.db")
    auth.create_db_and_tables()

    dependencies = []

    if server_api_key:

        async def verify_api_key(
            x_api_key: Optional[str] = Header(None, alias="X-API-Key")
        ) -> None:
            if x_api_key != server_api_key:
                raise HTTPException(status_code=401, detail="Invalid API Key")

        dependencies.append(Depends(verify_api_key))

    app = FastAPI(title="Moogla API", dependencies=dependencies)

    if rate_limit:

        class RateLimitMiddleware:
            def __init__(self, app: FastAPI, limit: int, window: int = 60) -> None:
                self.app = app
                self.limit = limit
                self.window = window
                self.hits: dict[str, tuple[int, float]] = {}

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    client = scope.get("client")
                    if client:
                        ip = client[0]
                        now = time.time()
                        count, start = self.hits.get(ip, (0, now))
                        if now - start > self.window:
                            start = now
                            count = 0
                        count += 1
                        self.hits[ip] = (count, start)
                        if count > self.limit:
                            response = JSONResponse(
                                {"detail": "Too Many Requests"}, status_code=429
                            )
                            await response(scope, receive, send)
                            return
                await self.app(scope, receive, send)

        app.add_middleware(RateLimitMiddleware, limit=rate_limit)

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

    class UserIn(BaseModel):
        username: str
        password: str

    @app.post("/register")
    def register(user: UserIn):
        if auth.get_user(user.username):
            raise HTTPException(status_code=400, detail="User exists")
        auth.create_user(user.username, user.password)
        return {"status": "created"}

    @app.post("/login")
    def login(form_data: OAuth2PasswordRequestForm = Depends()):
        user = auth.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid credentials")
        token = auth.create_access_token({"sub": user.username})
        return {"access_token": token, "token_type": "bearer"}

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
    async def chat_completions(
        req: ChatRequest, user: auth.User = Depends(auth.get_current_user)
    ):
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
    async def completions(
        req: CompletionRequest, user: auth.User = Depends(auth.get_current_user)
    ):
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
        db_url=db_url,
    )
    uvicorn.run(app, host=host, port=port)
