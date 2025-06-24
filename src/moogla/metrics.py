from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

completions_total = Counter("completions_total", "Total completions served")
plugin_duration = Histogram(
    "plugin_execution_seconds",
    "Time spent executing plugins",
    ["plugin", "stage"],
)


def setup_metrics(app: FastAPI) -> None:
    """Instrument the application and expose Prometheus metrics."""
    Instrumentator().instrument(app).expose(app)

