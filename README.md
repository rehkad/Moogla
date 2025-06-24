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
moogla serve --plugin tests.dummy_plugin
```

Plugins can also be distributed as separate packages by exposing the
`moogla.plugins` entry point. A minimal `pyproject.toml` might look like:

```toml
[project.entry-points."moogla.plugins"]
example = "my_plugin.module"
```

After installing the package, the plugin will be picked up automatically
without passing `--plugin` on the command line.

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

## Contributing Guidelines

- Use the `src` layout for all packages and modules.
- Keep functions small and composable.
- Write unit tests for new behavior in `tests/`.
- Use type hints and docstrings.

