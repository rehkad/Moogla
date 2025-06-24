from fastapi.testclient import TestClient

from moogla.server import create_app


def test_chat_completion():
    app = create_app()
    client = TestClient(app)
    resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "olleh"


def test_completion_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.post("/v1/completions", json={"prompt": "abc"})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["text"] == "cba"


def test_plugins():
    app = create_app(["tests.dummy_plugin"])
    client = TestClient(app)
    resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "!!OLLEH!!"


def test_root_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Moogla Chat" in resp.text
