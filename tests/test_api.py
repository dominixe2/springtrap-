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


def test_home_page_exposes_memory_controls_and_local_privacy_warning():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="memoryForm"' in response.text
    assert 'id="memoryList"' in response.text
    assert "Neukládej sem hesla ani tajné klíče" in response.text
    assert "/v1/conversations" in response.text


def test_chat_uses_local_memory_and_persists_successful_exchange(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "Ahoj, jsem Mykla."}}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    client_memory = client.post(
        "/v1/memories",
        json={"content": "Uživatel chce odpovědi česky", "category": "preference"},
    )
    assert client_memory.status_code == 201
    monkeypatch.setattr(api.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post("/v1/chat", json={"message": "Ahoj", "model": "llama3.2"})
    assert response.status_code == 200
    assert response.json()["reply"] == "Ahoj, jsem Mykla."
    assert "Uživatel chce odpovědi česky" in captured["payload"]["messages"][0]["content"]
    saved = client.get("/v1/conversations").json()["messages"]
    assert [item["role"] for item in saved] == ["user", "assistant"]
    assert saved[0]["content"] == "Ahoj"
