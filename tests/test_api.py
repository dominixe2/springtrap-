from fastapi.testclient import TestClient
from micro_helper.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "micro-helper"}


def test_status_is_honest_about_scope():
    response = client.get("/v1/status")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == "Micro Helper"
    assert body["paid_api_required"] is False
    assert "llm_chat" in body["not_yet_implemented"]
