from fastapi.testclient import TestClient
from moogla.server import app

client = TestClient(app)

def test_health_check():
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


def test_ui_page():
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'Moogla UI' in resp.text


def test_echo():
    resp = client.post('/echo', json={'message': 'hi'})
    assert resp.status_code == 200
    assert resp.json() == {'echo': 'hi'}
