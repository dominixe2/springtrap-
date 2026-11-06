from pathlib import Path

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
    assert "browser_voice_input_output" in body["implemented"]
    assert "realtime_voice_streaming" in body["not_yet_implemented"]
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


def test_memory_can_be_corrected_and_deleted():
    created = client.post("/v1/memories", json={"content": "old note", "category": "context"})
    memory_id = created.json()["id"]
    updated = client.put(
        f"/v1/memories/{memory_id}",
        json={"content": "corrected note", "category": "goal"},
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "corrected note"
    assert updated.json()["category"] == "goal"
    assert client.put(
        f"/v1/memories/{memory_id + 9999}",
        json={"content": "missing", "category": "context"},
    ).status_code == 404


def test_memory_ui_supports_edit_and_export():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="exportMemory"' in response.text
    assert 'textContent="Upravit"' in response.text
    assert 'method:"PUT"' in response.text
    assert 'micro-helper-memory.json' in response.text


def test_full_backup_round_trip_restores_profile_memories_and_messages():
    client.put("/v1/profile", json={"agent_name": "Mykla", "language": "cs-CZ", "style": "stručný"})
    client.post("/v1/memories", json={"content": "Testovací paměť", "category": "project"})
    with api.database() as db:
        db.execute("INSERT INTO messages(role, content, created_at) VALUES ('user', 'Ahoj', '2026-01-01T00:00:00Z')")
        db.execute("INSERT INTO messages(role, content, created_at) VALUES ('assistant', 'Čau', '2026-01-01T00:00:01Z')")
        db.commit()
    backup = client.get("/v1/backup").json()
    assert backup["format"] == "micro-helper-backup"
    assert len(backup["memories"]) == 1
    assert len(backup["messages"]) == 2

    client.put("/v1/profile", json={"agent_name": "Other", "language": "cs-CZ", "style": "friendly"})
    client.post("/v1/memories", json={"content": "Nová poznámka", "category": "context"})
    assert client.post("/v1/backup/restore", json={"backup": backup}).status_code == 400

    restored = client.post("/v1/backup/restore", json={"backup": backup, "confirm_replace": True})
    assert restored.status_code == 200
    assert restored.json() == {"restored": True, "memories": 1, "messages": 2, "tasks": 0}
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"
    assert [m["content"] for m in client.get("/v1/memories").json()["memories"]] == ["Testovací paměť"]
    assert [m["content"] for m in client.get("/v1/conversations").json()["messages"]] == ["Ahoj", "Čau"]


def test_restore_rejects_invalid_backup():
    response = client.post("/v1/backup/restore", json={
        "backup": {"format": "wrong", "version": 1, "profile": {}, "memories": [], "messages": []},
        "confirm_replace": True,
    })
    assert response.status_code == 422


def test_launch_scripts_bind_only_to_loopback():
    repo_root = Path(__file__).resolve().parents[1]
    for script in ("run-windows.bat", "termux-start.sh"):
        content = (repo_root / script).read_text(encoding="utf-8")
        assert "--host 127.0.0.1" in content, f"{script} must not expose private APIs on the LAN"


def test_home_page_exposes_czech_browser_voice_controls():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="voiceInput"' in response.text
    assert 'id="voiceOutput"' in response.text
    assert 'id="voiceStop"' in response.text
    assert 'recognition.lang="cs-CZ"' in response.text
    assert 'utterance.lang="cs-CZ"' in response.text


def test_legacy_v1_backup_without_tasks_restores_existing_data():
    """Older v1 exports did not always include the tasks key."""
    legacy_backup = {
        "format": "micro-helper-backup",
        "version": 1,
        "exported_at": "2026-01-01T00:00:00+00:00",
        "profile": {
            "agent_name": "Mykla",
            "language": "cs-CZ",
            "style": "stručný",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        "memories": [
            {"id": 7, "content": "Původní paměť", "category": "preference", "created_at": "2026-01-01T00:00:00+00:00"}
        ],
        "messages": [
            {"id": 11, "role": "user", "content": "Starší zpráva", "created_at": "2026-01-01T00:00:01+00:00"}
        ],
    }

    response = client.post(
        "/v1/backup/restore",
        json={"backup": legacy_backup, "confirm_replace": True},
    )

    assert response.status_code == 200
    assert response.json() == {"restored": True, "memories": 1, "messages": 1, "tasks": 0}
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"
    assert client.get("/v1/memories").json()["memories"][0]["content"] == "Původní paměť"
    assert client.get("/v1/conversations").json()["messages"][0]["content"] == "Starší zpráva"
    assert client.get("/v1/tasks").json()["tasks"] == []


def test_backup_round_trip_preserves_tasks_and_all_existing_records():
    client.put("/v1/profile", json={"agent_name": "Mykla", "language": "cs-CZ", "style": "stručný"})
    client.post("/v1/memories", json={"content": "Důležitá paměť", "category": "project"})
    client.post("/v1/tasks", json={
        "title": "Dokončit Micro Helper",
        "description": "Zachovat historii a úkoly",
        "due_at": "2026-12-01T12:00:00+01:00",
    })
    with api.database() as db:
        db.execute(
            "INSERT INTO messages(role, content, created_at) VALUES (?, ?, ?)",
            ("user", "Původní zpráva", "2026-01-01T00:00:00Z"),
        )
        db.commit()

    backup = client.get("/v1/backup").json()
    assert len(backup["tasks"]) == 1

    client.put("/v1/profile", json={"agent_name": "Jiný profil", "language": "cs-CZ", "style": "friendly"})
    client.post("/v1/tasks", json={"title": "Dočasný úkol"})

    restored = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert restored.status_code == 200
    assert restored.json() == {"restored": True, "memories": 1, "messages": 1, "tasks": 1}
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"
    assert [item["content"] for item in client.get("/v1/memories").json()["memories"]] == ["Důležitá paměť"]
    assert [item["title"] for item in client.get("/v1/tasks").json()["tasks"]] == ["Dokončit Micro Helper"]
    assert [item["content"] for item in client.get("/v1/conversations").json()["messages"]] == ["Původní zpráva"]


def test_invalid_task_in_backup_does_not_replace_existing_user_data():
    client.put("/v1/profile", json={"agent_name": "Bezpečný profil", "language": "cs-CZ", "style": "stručný"})
    client.post("/v1/memories", json={"content": "Zachovat mě", "category": "preference"})
    client.post("/v1/tasks", json={"title": "Zachovat úkol"})
    backup = client.get("/v1/backup").json()
    backup["tasks"] = [{"id": "neplatné-id", "title": "Rozbitý úkol", "created_at": "now"}]

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 422
    assert client.get("/v1/profile").json()["agent_name"] == "Bezpečný profil"
    assert [item["content"] for item in client.get("/v1/memories").json()["memories"]] == ["Zachovat mě"]
    assert [item["title"] for item in client.get("/v1/tasks").json()["tasks"]] == ["Zachovat úkol"]

def test_restore_rejects_coerced_task_completion_and_preserves_existing_data():
    client.put("/v1/profile", json={"agent_name": "Bezpečný profil", "language": "cs-CZ", "style": "stručný"})
    client.post("/v1/memories", json={"content": "Zachovat mě", "category": "preference"})
    client.post("/v1/tasks", json={"title": "Zachovat úkol"})
    backup = client.get("/v1/backup").json()
    backup["tasks"][0]["completed"] = "false"

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 422
    assert client.get("/v1/profile").json()["agent_name"] == "Bezpečný profil"
    assert [item["content"] for item in client.get("/v1/memories").json()["memories"]] == ["Zachovat mě"]
    assert [item["title"] for item in client.get("/v1/tasks").json()["tasks"]] == ["Zachovat úkol"]


def test_restore_rejects_duplicate_record_ids_before_replacing_data():
    client.post("/v1/memories", json={"content": "Původní paměť", "category": "preference"})
    backup = client.get("/v1/backup").json()
    backup["memories"].append({**backup["memories"][0], "content": "Duplicitní záznam"})

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 422
    assert [item["content"] for item in client.get("/v1/memories").json()["memories"]] == ["Původní paměť"]


def test_restore_rejects_non_string_memory_content_instead_of_coercing_it():
    backup = client.get("/v1/backup").json()
    backup["memories"] = [{"id": 1, "content": 123, "category": "preference", "created_at": "2026-01-01T00:00:00Z"}]

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 422
    assert client.get("/v1/memories").json()["memories"] == []

