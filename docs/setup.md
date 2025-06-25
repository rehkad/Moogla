# Setup

The project requires Python 3.9 or newer. A helper script is provided to
create a virtual environment and install dependencies.

```bash
./scripts/setup.sh
```

To install development tools run:

```bash
pip install -e .[dev]
```

Run the CLI to see available commands:

```bash
moogla --help
```

### Models Directory

By default `moogla pull` stores downloaded models in `~/.cache/moogla/models`.
Set `MOOGLA_MODEL_DIR` to choose a different location. All commands that use
local models will look for files in this directory.

List cached models with `moogla models` and remove one using `moogla remove <name>`.
