from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Moogla API")

@app.get("/health")
def health_check():
    return {"status": "ok"}


class EchoRequest(BaseModel):
    """Payload for echo endpoint."""

    message: str


@app.get("/", response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    """Serve a minimal web UI."""
    html = """<!DOCTYPE html>
<html>
<head>
  <title>Moogla UI</title>
</head>
<body>
  <h1>Moogla UI</h1>
  <div>
    <input id=\"message\" placeholder=\"Type a message\" />
    <button onclick=\"send()\">Send</button>
  </div>
  <pre id=\"response\"></pre>
  <script>
    async function send() {
      const msg = document.getElementById('message').value;
      const res = await fetch('/echo', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
      });
      const data = await res.json();
      document.getElementById('response').textContent = JSON.stringify(data, null, 2);
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/echo")
def echo(payload: EchoRequest):
    """Echo back the provided message."""
    return {"echo": payload.message}

def start_server(host: str = "0.0.0.0", port: int = 11434) -> None:
    """Run the HTTP server."""
    uvicorn.run(app, host=host, port=port)
