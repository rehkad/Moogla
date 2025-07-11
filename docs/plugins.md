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
moogla plugin add my_plugin --set greeting=hello --set retries=3
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

## Plugin Settings

Additional options for a plugin can be stored alongside its name in the
configuration file. When a plugin defines a `setup(settings: dict)` function,
those settings are passed to it on load. When adding a plugin via the CLI you
can provide settings with the `--set` option:

```bash
moogla plugin add my_plugin --set greeting=hello --set retries=3
```

Example YAML structure:

```yaml
plugins:
  - my_plugin
settings:
  my_plugin:
    greeting: hello
```

Within the plugin you can read the settings during setup:

```python
# my_plugin.py
config = {}

def setup(settings: dict) -> None:
    config.update(settings)

def preprocess(text: str) -> str:
    return f"{config.get('greeting', '')}{text}"
```

Settings are automatically provided when running `moogla serve` or creating the
application programmatically.


## Teardown Hooks

Plugins can also clean up resources when the application shuts down. Define a
`teardown` or `teardown_async` function in the plugin module and it will be
called during application shutdown.

```python
# my_plugin.py
async def teardown_async() -> None:
    await connection.close()
```

## Live Reloads

Running servers can refresh plugins without restarting. After editing the
configuration or plugin files, call the `/reload-plugins` endpoint or use the
CLI command:

```bash
moogla reload-plugins
```

The server will invoke `load_plugins` again and apply any new settings.
