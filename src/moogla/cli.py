from typing import List
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

import typer

from .server import start_server

app = typer.Typer(help="Moogla command line interface")

@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 11434,
    plugin: List[str] = typer.Option(
        None, '--plugin', '-p', help='Plugin module to load', show_default=False
    ),
):
    """Start the Moogla HTTP server.

    Parameters
    ----------
    host: IP or hostname to bind.
    port: TCP port to listen on.
    plugin: Optional plugin modules to initialize.
    """
    start_server(host=host, port=port, plugin_names=plugin)


DEFAULT_DIR = Path.home() / ".cache" / "moogla" / "models"


@app.command()
def pull(
    model: str,
    dir: Path = typer.Option(None, "--dir", "-d", help="Directory for downloaded models"),
):
    """Download a model into the local cache.

    Parameters
    ----------
    model: Identifier, path or URL of the model to fetch.
    dir: Target directory for the downloaded file.
    """
    dest_dir = dir or Path(os.getenv("MOOGLA_MODEL_DIR", DEFAULT_DIR))
    dest_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(model)
    filename = Path(parsed.path).name or "model"
    dest = dest_dir / filename

    if dest.exists():
        typer.echo(f"Using cached model at {dest}")
        return

    if parsed.scheme in {"http", "https", "file"}:
        url = model
        with httpx.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with open(dest, "wb") as f, typer.progressbar(
                length=total or None, label="Downloading"
            ) as bar:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
                    if total:
                        bar.update(len(chunk))
    elif Path(model).is_file():
        size = os.path.getsize(model)
        with open(model, "rb") as src, open(dest, "wb") as dst, typer.progressbar(
            length=size, label="Downloading"
        ) as bar:
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

if __name__ == "__main__":
    app()
