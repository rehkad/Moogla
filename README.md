# Moogla

Moogla is a self‑hosted LLM runtime and orchestration framework for power users.
It combines local‑first execution with the flexibility required for
production‑grade workflows.  The repository starts with a minimal project layout
that lets new features be added incrementally while keeping the codebase
modular, observable and developer friendly.

## Features

- Local execution and a simple plugin system
- FastAPI server exposing OpenAI compatible endpoints
- Built‑in web UI located in `src/moogla/web`
- Example tests showing how to extend the framework

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

To use a Hugging Face model ID instead of a file path:

```bash
moogla serve --model mistralai/Mistral-7B-Instruct-v0.2
```

You can then query the chat completion endpoint:

```bash
curl -X POST http://localhost:11434/v1/chat/completions \
  -d '{"messages": [{"role": "user", "content": "hello"}]}'
```

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

The API also exposes `/register` and `/login` endpoints for JWT authentication.
Send a username and password to `/register` to create a user, then call `/login`
to retrieve a token. Include this token when calling the LLM routes by adding an
`Authorization: Bearer <token>` header. Authentication support relies on the
`SQLModel`, `passlib` and `python-jose` packages.

## Running with Docker

Build the image and start the server:

```bash
docker build -t moogla .
docker run -p 11434:11434 moogla
```

You can also use `docker-compose` to mount a models directory and supply
environment variables:

```bash
docker-compose up
```


## Contributing Guidelines

- Use the `src` layout for all packages and modules.
- Keep functions small and composable.
- Write unit tests for new behavior in `tests/`.
- Use type hints and docstrings.

