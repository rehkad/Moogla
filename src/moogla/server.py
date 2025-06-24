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
from sqlmodel import SQLModel, Session, create_engine, select
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

from .auth import User

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
    if db_url:
        os.environ["MOOGLA_PLUGIN_DB"] = db_url.replace("sqlite:///", "")
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

    engine = create_engine(db_url or "sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret_key = os.getenv("MOOGLA_JWT_SECRET", "secret")
    algorithm = "HS256"

    dependencies = []

    if server_api_key:

        async def verify_auth(
            x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
            authorization: Optional[str] = Header(None, alias="Authorization"),
        ) -> None:
            if x_api_key == server_api_key:
                return
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ", 1)[1]
                try:
                    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
                    user_id = int(payload.get("sub"))
                except JWTError:
                    raise HTTPException(status_code=401, detail="Invalid API Key")
                with Session(engine) as session:
                    if not session.get(User, user_id):
                        raise HTTPException(status_code=401, detail="Invalid API Key")
                return
            raise HTTPException(status_code=401, detail="Invalid API Key")

        auth_dependency = Depends(verify_auth)
    else:
        auth_dependency = None

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
    app.state.engine = engine
    app.state.pwd_context = pwd_context
    app.state.jwt_secret = secret_key
    app.state.jwt_algorithm = algorithm

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

    class Credentials(BaseModel):
        username: str
        password: str

    @app.post("/register", status_code=201)
    def register(creds: Credentials):
        with Session(engine) as session:
            existing = session.exec(select(User).where(User.username == creds.username)).first()
            if existing:
                raise HTTPException(status_code=400, detail="User exists")
            user = User(username=creds.username, hashed_password=pwd_context.hash(creds.password))
            session.add(user)
            session.commit()
            session.refresh(user)
            return {"id": user.id, "username": user.username}

    @app.post("/login")
    def login(creds: Credentials):
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == creds.username)).first()
            if not user or not pwd_context.verify(creds.password, user.hashed_password):
                raise HTTPException(status_code=401, detail="Invalid credentials")
        payload = {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(minutes=30)}
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
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

    route_args = {"dependencies": [auth_dependency]} if auth_dependency else {}

    @app.post("/v1/chat/completions", **route_args)
    async def chat_completions(req: ChatRequest):
        """Handle Chat API calls and return a reversed assistant reply."""
        if not req.messages:
            return {"choices": []}
        content = req.messages[-1].content
        if req.stream:
            async def event_stream():
                text = content
                for plugin in plugins:
                    try:
                        text = await plugin.run_preprocess(text)
                    except Exception as exc:
                        logger.exception("Preprocess plugin failed: %s", exc)
                        raise HTTPException(status_code=500, detail="Plugin error") from exc

                async for token in executor.astream(text):
                    yield json.dumps({"choices": [{"delta": {"content": token}}]}) + "\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        reply = await apply_plugins(content)
        return {"choices": [{"message": {"role": "assistant", "content": reply}}]}

    @app.post("/v1/completions", **route_args)
    async def completions(req: CompletionRequest):
        """Return a completion for the given prompt using the mock backend."""
        if req.stream:
            async def event_stream():
                text = req.prompt
                for plugin in plugins:
                    try:
                        text = await plugin.run_preprocess(text)
                    except Exception as exc:
                        logger.exception("Preprocess plugin failed: %s", exc)
                        raise HTTPException(status_code=500, detail="Plugin error") from exc

                async for token in executor.astream(text):
                    yield json.dumps({"choices": [{"delta": {"content": token}}]}) + "\n"

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
