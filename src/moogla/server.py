from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Moogla API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


def start_server(host: str = "0.0.0.0", port: int = 11434) -> None:
    """Run the HTTP server."""
    uvicorn.run(app, host=host, port=port)
