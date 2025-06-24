# Plugin Development

Moogla can load custom plugins to modify prompts and responses. A plugin
is a Python module that exposes optional `preprocess` and `postprocess`
functions.

Example plugin:

```python
# my_plugin.py

def preprocess(text: str) -> str:
    return text.upper()

def postprocess(text: str) -> str:
    return f"!!{text}!!"
```

Plugins can be loaded at startup using `--plugin`:

```bash
moogla serve --plugin my_plugin
```

You can also persist plugin names using the CLI. Plugin information is stored in
a YAML or JSON file (by default `~/.cache/moogla/plugins.yaml`).

```bash
moogla plugin add my_plugin
moogla plugin list
moogla plugin remove my_plugin
```

The file location can be customised with the `--config` option or the
`MOOGLA_PLUGIN_FILE` environment variable. Both override the default
path for all plugin commands:

```bash
export MOOGLA_PLUGIN_FILE=/path/to/plugins.json
moogla plugin add my_plugin
```
