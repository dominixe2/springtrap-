from fastapi.testclient import TestClient
import pytest
import micro_helper.api as api


client = TestClient(api.app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    # Keep tests hermetic and independent of a real user's home directory.
    api.DATABASE_PATH = tmp_path / "micro-helper-tests.sqlite3"


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
    assert "ollama_chat_adapter" in body["implemented"]
    assert "persistent_local_memory" in body["implemented"]
    assert "voice" in body["not_yet_implemented"]
    assert body["storage"]["type"] == "local_sqlite"


def test_profile_persists_and_validates():
    saved = client.put("/v1/profile", json={"agent_name": "Nova", "language": "cs-CZ", "style": "stručný"})
    assert saved.status_code == 200
    assert saved.json()["agent_name"] == "Nova"
    assert client.get("/v1/profile").json()["style"] == "stručný"
    assert client.put("/v1/profile", json={"agent_name": "", "language": "cs-CZ", "style": "friendly"}).status_code == 422


def test_memory_crud_and_conversation_history():
    created = client.post("/v1/memories", json={"content": "Uživatel preferuje češtinu", "category": "preference"})
    assert created.status_code == 201
    memory = created.json()
    assert memory["content"] == "Uživatel preferuje češtinu"
    assert client.get("/v1/memories").json()["memories"][0]["id"] == memory["id"]
    assert client.delete(f"/v1/memories/{memory['id']}").json()["deleted"] is True
    assert client.delete(f"/v1/memories/{memory['id']}").status_code == 404


def test_conversation_clear_endpoint():
    with api.database() as db:
        db.execute("INSERT INTO messages(role, content, created_at) VALUES ('user', 'test', 'now')")
        db.commit()
    assert len(client.get("/v1/conversations").json()["messages"]) == 1
    assert client.delete("/v1/conversations").json()["deleted"] is True
    assert client.get("/v1/conversations").json()["messages"] == []


def test_chat_rejects_invalid_model_name_before_network_call():
    response = client.post("/v1/chat", json={"message": "Ahoj", "model": "../something"})
    assert response.status_code == 422
