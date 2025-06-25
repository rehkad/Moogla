import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, select

from . import plugins_config
from .auth import User
from .config import Settings
from .executor import LLMExecutor
from .plugins import load_plugins

logger = logging.getLogger(__name__)


def create_app(
    plugin_names: Optional[List[str]] = None,
    *,
    settings: Optional[Settings] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    server_api_key: Optional[str] = None,
    rate_limit: Optional[int] = None,
    redis_url: Optional[str] = None,
    db_url: Optional[str] = None,
    plugin_file: Optional[str] = None,
    jwt_secret: Optional[str] = None,
    token_exp_minutes: Optional[int] = None,
) -> FastAPI:
    """Build the FastAPI application."""
    settings = settings or Settings()
    model = model or settings.model
    api_key = api_key or settings.openai_api_key
    api_base = api_base or settings.openai_api_base
    server_api_key = server_api_key or settings.server_api_key
    if rate_limit is None:
        rate_limit = settings.rate_limit
    redis_url = redis_url or settings.redis_url
    db_url = db_url or settings.db_url
    plugin_file = plugin_file or settings.plugin_file
    secret_key = jwt_secret or settings.jwt_secret
    token_exp_minutes = (
        token_exp_minutes if token_exp_minutes is not None else settings.token_exp_minutes
    )
    algorithm = "HS256"

    if jwt_secret is None and "MOOGLA_JWT_SECRET" not in os.environ:
        logger.warning(
            "Generated ephemeral JWT secret. Set MOOGLA_JWT_SECRET to persist tokens."
        )
    if db_url == "sqlite:///:memory:":
        logger.warning("Using in-memory SQLite database; user data will not persist.")

    plugins_config.set_plugin_file(str(plugin_file) if plugin_file else None)

    plugins = load_plugins(plugin_names)

    executor = LLMExecutor(model=model, api_key=api_key, api_base=api_base)

    engine = create_engine(db_url or "sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

    lifespan = None
    if rate_limit:
        @asynccontextmanager
        async def lifespan(_: FastAPI):
            import redis.asyncio as redis

            redis_conn = redis.from_url(
                redis_url, encoding="utf8", decode_responses=True
            )
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
            existing = session.exec(
                select(User).where(User.username == creds.username)
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="User exists")
            user = User(
                username=creds.username,
                hashed_password=pwd_context.hash(creds.password),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return {"id": user.id, "username": user.username}

    @app.post("/login")
    def login(creds: Credentials):
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.username == creds.username)
            ).first()
            if not user or not pwd_context.verify(creds.password, user.hashed_password):
                raise HTTPException(status_code=401, detail="Invalid credentials")
        payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() + timedelta(minutes=token_exp_minutes),
        }
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        return {"access_token": token, "token_type": "bearer"}

    class Message(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        messages: List[Message]
        stream: bool = False
        max_tokens: Optional[int] = None
        temperature: Optional[float] = None
        top_p: Optional[float] = None

    class CompletionRequest(BaseModel):
        prompt: str
        stream: bool = False
        max_tokens: Optional[int] = None
        temperature: Optional[float] = None
        top_p: Optional[float] = None

    async def apply_plugins(
        text: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        """Run text through plugin hooks and return the mock LLM output."""
        for plugin in plugins:
            try:
                text = await plugin.run_preprocess(text)
            except Exception as exc:
                logger.exception("Preprocess plugin failed: %s", exc)
                raise HTTPException(status_code=500, detail="Plugin error") from exc
        response = await executor.acomplete(
            text,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        for plugin in plugins:
            try:
                response = await plugin.run_postprocess(response)
            except Exception as exc:
                logger.exception("Postprocess plugin failed: %s", exc)
                raise HTTPException(status_code=500, detail="Plugin error") from exc
        return response

    route_args = {"dependencies": [auth_dependency]} if auth_dependency else {}

    class PasswordChange(BaseModel):
        username: str
        old_password: str
        new_password: str

    @app.get("/users", **route_args)
    def list_users():
        with Session(engine) as session:
            users = session.exec(select(User)).all()
            return [{"id": u.id, "username": u.username} for u in users]

    @app.post("/change-password", **route_args)
    def change_password(change: PasswordChange):
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.username == change.username)
            ).first()
            if not user or not pwd_context.verify(
                change.old_password, user.hashed_password
            ):
                raise HTTPException(status_code=400, detail="Invalid credentials")
            user.hashed_password = pwd_context.hash(change.new_password)
            session.add(user)
            session.commit()
        return {"status": "ok"}

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
                        raise HTTPException(
                            status_code=500, detail="Plugin error"
                        ) from exc

                async for token in executor.astream(
                    text,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_p=req.top_p,
                ):
                    yield json.dumps(
                        {"choices": [{"delta": {"content": token}}]}
                    ) + "\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        reply = await apply_plugins(
            content,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )
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
                        raise HTTPException(
                            status_code=500, detail="Plugin error"
                        ) from exc

                async for token in executor.astream(
                    text,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_p=req.top_p,
                ):
                    yield json.dumps(
                        {"choices": [{"delta": {"content": token}}]}
                    ) + "\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        reply = await apply_plugins(
            req.prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )
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
    plugin_file: Optional[str] = None,
    jwt_secret: Optional[str] = None,
    token_exp_minutes: Optional[int] = None,
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
        plugin_file=plugin_file,
        jwt_secret=jwt_secret,
        token_exp_minutes=token_exp_minutes,
    )
    uvicorn.run(app, host=host, port=port)
