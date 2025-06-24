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

The file location can be customised with `--config`:

```bash
moogla plugin --config /path/to/plugins.json add my_plugin
```

Plugins can also define an optional `init` function which receives any
stored configuration for the plugin. The settings are provided when the
plugin module is imported:

```python
# my_plugin.py

def init(settings: dict):
    print("initialising with", settings)
```

Settings can be saved programmatically with `plugins_config.add_plugin`
or by editing the configuration file directly.
