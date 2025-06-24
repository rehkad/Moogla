# Moogla

Moogla is a self‑hosted LLM runtime and orchestration framework for power users. It combines
local-first execution with the flexibility required for production‑grade workflows.

This repository starts with a minimal project layout and conventions so that new
features can be added incrementally. The goal is to keep the codebase modular,
observable and developer friendly.

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

1. Run the setup script to create a virtual environment and install dependencies:

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

You can then query the chat completion endpoint:

```bash
curl -X POST http://localhost:11434/v1/chat/completions \
  -d '{"messages": [{"role": "user", "content": "hello"}]}'
```

## Contributing Guidelines

- Use the `src` layout for all packages and modules.
- Keep functions small and composable.
- Write unit tests for new behavior in `tests/`.
- Use type hints and docstrings.

