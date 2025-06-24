from typing import List

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


@app.command()
def pull(model: str):
    """Download a model into the local cache (stub).

    Parameters
    ----------
    model: Identifier of the model to fetch.
    """
    typer.echo(f"Pulling {model} ... done.")

if __name__ == "__main__":
    app()
