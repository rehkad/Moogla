from fastapi.testclient import TestClient
from moogla.server import create_app


def test_static_ui_served():
    app = create_app()
    client = TestClient(app)
    resp = client.get('/app')
    assert resp.status_code == 200
    assert '<!DOCTYPE html>' in resp.text
