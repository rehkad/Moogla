# Moogla

[![codecov](https://codecov.io/gh/example/Moogla/branch/main/graph/badge.svg)](https://codecov.io/gh/example/Moogla)

Moogla is a self‑hosted LLM runtime and orchestration framework for power users.
It combines local‑first execution with the flexibility required for
production‑grade workflows.  The repository starts with a minimal project layout
that lets new features be added incrementally while keeping the codebase
modular, observable and developer friendly.

## Features

- Local or remote model execution with streaming responses
- Expandable plugin system with async hooks and CLI management
- FastAPI server exposing OpenAI compatible endpoints
- Small /version endpoint for health checks and client introspection
- Optional API authentication via API key or JWT
- Redis‑backed rate limiting
- Built‑in dark‑mode web UI with file uploads and quick hints
- Command to download models for offline use
- Command to list available local models
- Live plugin reloads via CLI command
- Docker setup for containerised deployment
- Example tests demonstrating extensibility

## Project Layout

```
.
├── src/            # Python package source
│   └── moogla/     # Moogla core modules
├── tests/          # Unit and integration tests
├── pyproject.toml  # Build system and dependency configuration
└── README.md
```

## Getting Started

1. Run the setup script to create a virtual environment and install
   dependencies:

   ```bash
   ./scripts/setup.sh
   ```

   When you want the development tools, install the optional extras:

   ```bash
   pip install -e .[dev]
   ```

2. After installation, run the CLI to see available commands:

   ```bash
   moogla --help
   ```

### Example Usage

Pull a model and start the server with a custom plugin:

```bash
moogla pull codellama:13b
moogla serve --model path/to/codellama-13b.gguf --plugin tests.dummy_plugin
```
Models are stored under `~/.cache/moogla/models` by default. Set `MOOGLA_MODEL_DIR` before running the pull command to use a different directory.

List downloaded files with:

```bash
moogla models
```

Remove a cached model with:

```bash
moogla remove model.bin
```
Use `-y` to skip the confirmation prompt:

```bash
moogla remove model.bin -y
```

To use a Hugging Face model ID instead of a file path:

```bash
moogla serve --model mistralai/Mistral-7B-Instruct-v0.2
```

You can then query the chat completion endpoint:

```bash
curl -X POST http://localhost:11434/v1/chat/completions \
  -d '{"messages": [{"role": "user", "content": "hello"}]}'
```

The request body may also include ``max_tokens``, ``temperature`` and ``top_p``
fields:

```bash
curl -X POST http://localhost:11434/v1/chat/completions \
  -d '{"messages": [{"role": "user", "content": "hello"}], "max_tokens": 32, "temperature": 0.7}'
```

### Plugin API

Plugins are regular Python modules that expose optional `preprocess` and
`postprocess` hooks. Asynchronous variants named `preprocess_async` and
`postprocess_async` are also supported. Hooks receive the current text and
return the modified value.

A plugin can specify an integer `order` attribute to control execution order
when multiple plugins are loaded. Lower numbers run first.

Plugin information is stored in `~/.cache/moogla/plugins.yaml` by default.
Use `--config` or the `MOOGLA_PLUGIN_FILE` environment variable to point
to a different location:

```bash
MOOGLA_PLUGIN_FILE=/opt/plugins.json moogla plugin list
```

Running servers can refresh plugins on demand with:

```bash
moogla reload-plugins
```

This calls the `/reload-plugins` endpoint and reloads modules using the
current configuration.

### Async Limitations

Local models loaded through `llama-cpp-python` do not expose an asynchronous
interface. When `LLMExecutor.acomplete` is called with such a model, inference
runs in a background thread via `asyncio.to_thread`. Heavy local workloads can
therefore limit overall throughput compared to fully async providers.

## Development Setup

The project uses [Typer](https://typer.tiangolo.com/) for the CLI and
[FastAPI](https://fastapi.tiangolo.com/) for the server. A helper script is
provided for creating a virtual environment and installing the optional
development tools:

```bash
./scripts/setup.sh -d -t
```

During development you can run the server with auto reload using `uvicorn`:

```bash
uvicorn moogla.server:create_app --reload
```

## Running Tests

Before running the test suite make sure the development extras are installed:

```bash
pip install -e .[dev]
pytest
```

### Web Interface

To try the browser UI run the server and open the bundled web app:

```bash
moogla serve
```

Then navigate to [http://localhost:11434/app](http://localhost:11434/app).
Double‑click a chat bubble to copy its contents and use the dark‑mode toggle in
the header to switch themes.

### API Authentication

Set `MOOGLA_API_KEY` to enable simple header based authentication. Requests must
include an `X-API-Key` header matching the configured value. Optionally set
`MOOGLA_RATE_LIMIT` to limit the number of requests per minute from a single IP.
When rate limiting is enabled, `MOOGLA_REDIS_URL` controls the Redis connection
used for tracking request counts (default `redis://localhost:6379`). These values
can also be passed to `create_app` or `moogla serve`.
Set `MOOGLA_CORS_ORIGINS` to send CORS headers for a comma-separated list of
allowed origins.
Set `MOOGLA_LOG_LEVEL` to control application logging (default `INFO`).
These values can also be provided via the `--cors-origins`, `--log-level` and
`--token-exp-minutes` options when running `moogla serve`.

The API also exposes `/register` and `/login` endpoints for JWT-based
authentication. POST a username and password to `/register` to persist a user
record, then call `/login` with the same credentials to obtain a token.
Include this token in an `Authorization: Bearer <token>` header when calling the
LLM routes. Tokens are signed with a random secret and stored in an in-memory
SQLite database by default. Set `MOOGLA_JWT_SECRET` and `MOOGLA_DB_URL` to keep
credentials valid across restarts. `MOOGLA_TOKEN_EXP_MINUTES` controls how long
issued tokens remain valid (default `30`). Authentication support relies on the
`SQLModel`, `passlib` and `python-jose` packages.

## Running with Docker

Build the image and start the server:

```bash
docker build -t moogla .
docker run -p 11434:11434 moogla
```
The Dockerfile now uses multi-stage builds so the final image only contains the
installed package and its runtime dependencies.

You can also use `docker-compose` to start the service with a few sensible
defaults. The compose file mounts a local `./models` directory into `/models`
inside the container and exposes port `11434`. Environment variables can be
used to configure remote providers and select the model to load. `MOOGLA_MODEL`
defaults to `codellama:13b` in the compose file and can be changed to any
local file or Hugging Face ID:

```bash
OPENAI_API_KEY=sk-... MOOGLA_MODEL=codellama:13b docker-compose up
```

The variables may also be placed in a `.env` file so they are picked up
automatically when running `docker-compose`.

## Configuring Persistent Storage

Authentication data is stored in an in-memory SQLite database by default, so
all user records disappear when the server stops. Point `MOOGLA_DB_URL` at a
real database to keep these records across restarts. Any SQLAlchemy compatible
URL can be used:

```bash
MOOGLA_DB_URL=sqlite:///data/moogla.db moogla serve
# or
MOOGLA_DB_URL=postgresql://user:pass@localhost/moogla moogla serve
```

Plugin information lives in `~/.cache/moogla/plugins.yaml`. Set
`MOOGLA_PLUGIN_FILE` (or use the `--config` flag) to choose a different
location. When running in Docker this file should be placed on a mounted
volume so plugin settings survive container restarts:

```bash
MOOGLA_PLUGIN_FILE=/data/plugins.yaml docker-compose up
```

Remember to back up your database and plugin configuration file. If the schema
changes in future versions you may need to migrate existing data before
upgrading.

## Documentation

Full documentation is available on GitHub Pages and can be built locally with:

```bash
mkdocs serve
```

## Packaging

Create a standalone binary using `pyinstaller`:

```bash
pip install pyinstaller
./scripts/build_package.sh dist/moogla.exe
```

Place the resulting file under `dist/` so `/download` can serve it.




## Contributing Guidelines

- Use the `src` layout for all packages and modules.
- Keep functions small and composable.
- Write unit tests for new behavior in `tests/`.
- Use type hints and docstrings.
- Install the pre-commit hooks with `pre-commit install`.

