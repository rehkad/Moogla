import typer
from .server import start_server

app = typer.Typer(help="Moogla command line interface")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 11434):
    """Start the Moogla HTTP server."""
    start_server(host=host, port=port)


if __name__ == "__main__":
    app()
