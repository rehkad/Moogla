import logging
import os
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import httpx
import typer
from dotenv import load_dotenv

from . import __version__, plugins_config
from .config import Settings
from .server import start_server

logger = logging.getLogger(__name__)

load_dotenv()

app = typer.Typer(help="Moogla command line interface")
plugin_app = typer.Typer(help="Manage plugins")
app.add_typer(plugin_app, name="plugin")


@plugin_app.callback()
def plugin_callback(
    config: str = typer.Option(
        None,
        "--config",
        help="Path to plugin configuration file",
        envvar="MOOGLA_PLUGIN_FILE",
        show_default=False,
    )
) -> None:
    if config:
        plugins_config.set_plugin_file(config)


@plugin_app.command("add")
def plugin_add(
    name: str,
    set_option: List[str] = typer.Option(
        None,
        "--set",
        "-s",
        help="Plugin setting in key=value form",
        metavar="KEY=VALUE",
    ),
) -> None:
    """Add a plugin to the persistent store."""
    settings = {}
    if set_option:
        for item in set_option:
            if "=" not in item:
                raise typer.BadParameter(
                    f"Invalid setting '{item}'", param_hint="--set"
                )
            key, value = item.split("=", 1)
            settings[key] = value
    plugins_config.add_plugin(name, **settings)
    typer.echo(f"Added {name}")


@plugin_app.command("remove")
def plugin_remove(name: str) -> None:
    """Remove a plugin from the store."""
    plugins_config.remove_plugin(name)
    typer.echo(f"Removed {name}")


@plugin_app.command("list")
def plugin_list() -> None:
    """List configured plugins."""
    names = plugins_config.get_plugins()
    if not names:
        typer.echo("No plugins configured")
    else:
        for n in names:
            typer.echo(n)


@plugin_app.command("show")
def plugin_show(name: str) -> None:
    """Show stored settings for a plugin."""
    settings = plugins_config.get_plugin_settings(name)
    if not settings:
        typer.echo(f"No settings for {name}")
    else:
        for k, v in settings.items():
            typer.echo(f"{k}={v}")


@plugin_app.command("clear")
def plugin_clear() -> None:
    """Remove all plugins from the store."""
    plugins_config.clear_plugins()
    typer.echo("Cleared plugin configuration")


@plugin_app.command("path")
def plugin_path() -> None:
    """Show the path to the plugin configuration file."""
    typer.echo(str(plugins_config.get_path()))


@app.command()
def version() -> None:
    """Show the installed Moogla version."""
    typer.echo(__version__)


@app.command()
def config() -> None:
    """Show the effective configuration values."""
    settings = Settings()
    typer.echo(settings.model_dump_json(indent=2))


@app.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="IP or hostname to bind",
        envvar="MOOGLA_HOST",
        show_default=True,
    ),
    port: int = typer.Option(
        11434,
        "--port",
        help="TCP port to listen on",
        envvar="MOOGLA_PORT",
        show_default=True,
    ),
    plugin: List[str] = typer.Option(
        None, "--plugin", "-p", help="Plugin module to load", show_default=False
    ),
    model: str = typer.Option(
        None,
        "--model",
        help="Model path or identifier",
        envvar="MOOGLA_MODEL",
        show_default=False,
    ),
    api_base: str = typer.Option(
        None,
        "--api-base",
        help="Base URL for remote API",
        envvar="OPENAI_API_BASE",
        show_default=False,
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="API key required for server access",
        envvar="MOOGLA_API_KEY",
        show_default=False,
    ),
    rate_limit: int = typer.Option(
        None,
        "--rate-limit",
        help="Requests per minute allowed per IP",
        envvar="MOOGLA_RATE_LIMIT",
        show_default=False,
    ),
    redis_url: str = typer.Option(
        None,
        "--redis-url",
        help="Redis connection string for rate limiting",
        envvar="MOOGLA_REDIS_URL",
        show_default=False,
    ),
    db_url: str = typer.Option(
        None,
        "--db-url",
        help="Database connection string",
        envvar="MOOGLA_DB_URL",
        show_default=False,
    ),
    jwt_secret: str = typer.Option(
        None,
        "--jwt-secret",
        help="Secret key for JWT tokens",
        envvar="MOOGLA_JWT_SECRET",
        show_default=False,
    ),
    plugin_file: str = typer.Option(
        None,
        "--plugin-file",
        help="Path to plugin configuration file",
        envvar="MOOGLA_PLUGIN_FILE",
        show_default=False,
    ),
    log_level: str = typer.Option(
        None,
        "--log-level",
        help="Logging level for the server",
        envvar="MOOGLA_LOG_LEVEL",
        show_default=False,
    ),
    cors_origins: str = typer.Option(
        None,
        "--cors-origins",
        help="Comma separated list of allowed CORS origins",
        envvar="MOOGLA_CORS_ORIGINS",
        show_default=False,
    ),
    token_exp_minutes: int = typer.Option(
        None,
        "--token-exp-minutes",
        help="JWT token expiry in minutes",
        envvar="MOOGLA_TOKEN_EXP_MINUTES",
        show_default=False,
    ),
):
    """Start the Moogla HTTP server.

    Parameters
    ----------
    host: IP or hostname to bind.
    port: TCP port to listen on.
    plugin: Optional plugin modules to initialize.
    db_url: Optional database connection string.

    The completion endpoints accept optional ``max_tokens``, ``temperature``
    and ``top_p`` fields to control generation.
    """
    start_server(
        host=host,
        port=port,
        plugin_names=plugin,
        model=model,
        api_base=api_base,
        server_api_key=api_key,
        rate_limit=rate_limit,
        redis_url=redis_url,
        db_url=db_url,
        jwt_secret=jwt_secret,
        plugin_file=plugin_file,
        log_level=log_level,
        cors_origins=cors_origins,
        token_exp_minutes=token_exp_minutes,
    )


@app.command()
def pull(
    model: str,
    directory: Path = typer.Option(
        None,
        "--directory",
        "-d",
        help="Directory to save downloaded models",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files",
        show_default=False,
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="HTTP download timeout in seconds",
        show_default=True,
    ),
):
    """Download a model into the local cache.

    Parameters
    ----------
    model: Identifier, path or URL of the model to fetch.
    directory: Target directory for the downloaded file.
    timeout: Maximum time in seconds to wait for HTTP downloads.
    force: Overwrite the destination file if it already exists.
    """
    settings = Settings()
    dest_dir = directory or settings.model_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(model)
    filename = Path(parsed.path).name or "model"
    dest = dest_dir / filename

    if dest.exists():
        if not force:
            typer.echo(f"Using cached model at {dest}")
            return
        dest.unlink()

    if parsed.scheme in {"http", "https", "file"}:
        url = model
        try:
            with httpx.stream("GET", url, timeout=timeout) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                with (
                    open(dest, "wb") as f,
                    typer.progressbar(length=total or None, label="Downloading") as bar,
                ):
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
                        if total:
                            bar.update(len(chunk))
        except Exception as exc:
            if dest.exists():
                dest.unlink()
            logger.error("Failed to download %s: %s", url, exc)
            typer.echo(f"Failed to download {url}: {exc}", err=True)
            raise typer.Exit(code=1)
    elif Path(model).is_file():
        size = os.path.getsize(model)
        with (
            open(model, "rb") as src,
            open(dest, "wb") as dst,
            typer.progressbar(length=size, label="Downloading") as bar,
        ):
            while True:
                data = src.read(8192)
                if not data:
                    break
                dst.write(data)
                bar.update(len(data))
    else:
        typer.echo(f"Unknown model source: {model}")
        raise typer.Exit(code=1)

    typer.echo(f"\nSaved to {dest}")


@app.command()
def models() -> None:
    """List model files in the configured directory."""
    settings = Settings()
    model_dir = settings.model_dir
    if not model_dir.is_dir():
        typer.echo("No models found")
        return

    names = sorted(p.name for p in model_dir.iterdir() if p.is_file())
    if not names:
        typer.echo("No models found")
    else:
        for n in names:
            typer.echo(n)


@app.command("reload-plugins")
def reload_plugins(
    url: str = typer.Option(
        "http://localhost:11434",
        "--url",
        help="Base URL of the running server",
        show_default=True,
    )
) -> None:
    """Trigger plugin reload on the running server."""
    target = url.rstrip("/") + "/reload-plugins"
    try:
        resp = httpx.post(target)
        resp.raise_for_status()
    except Exception as exc:
        typer.echo(f"Failed to reload plugins: {exc}", err=True)
        raise typer.Exit(code=1)
    plugins = resp.json().get("loaded", [])
    if plugins:
        typer.echo("\n".join(plugins))
    else:
        typer.echo("Plugins reloaded")


@app.command()
def remove(
    model: str,
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Delete without confirmation",
    ),
) -> None:
    """Delete a model file from the local cache."""
    settings = Settings()
    path = settings.model_dir / model

    if not path.exists():
        typer.echo(f"Model not found: {model}")
        raise typer.Exit(code=1)

    if not yes and not typer.confirm(f"Delete {path}?"):
        typer.echo("Aborted")
        raise typer.Exit(code=1)

    path.unlink()
    typer.echo(f"Deleted {path.name}")


if __name__ == "__main__":
    app()
