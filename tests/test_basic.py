import os
from fastapi.testclient import TestClient
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")

client = TestClient(create_app())

def test_health_check():
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}
