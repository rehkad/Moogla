from fastapi.testclient import TestClient
from moogla.server import create_app
from moogla import __version__


def test_version_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/version")
    assert resp.status_code == 200
    assert resp.json() == {"version": __version__}
