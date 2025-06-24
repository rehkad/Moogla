import os
import tempfile
from fastapi.testclient import TestClient
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")

tmp_db = tempfile.NamedTemporaryFile(delete=False)
client = TestClient(create_app(db_url=f"sqlite:///{tmp_db.name}"))

def test_health_check():
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}
