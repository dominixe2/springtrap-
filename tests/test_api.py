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
    assert "browser_voice_input" in body["implemented"]
    assert "browser_voice_output" in body["implemented"]
    assert "live_duplex_voice" in body["not_yet_implemented"]
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


def test_pwa_manifest_icon_and_service_worker_are_served():
    manifest = client.get("/static/manifest.webmanifest")
    icon = client.get("/static/icon.svg")
    worker = client.get("/sw.js")
    assert manifest.status_code == 200
    assert manifest.json()["name"] == "Micro Helper"
    assert icon.status_code == 200
    assert "<svg" in icon.text
    assert worker.status_code == 200
    assert "micro-helper-pwa-v1" in worker.text


def test_home_page_has_offline_local_fallback():
    response = client.get("/")
    assert response.status_code == 200
    assert "micro_helper_offline_v1" in response.text
    assert "offline-local" in response.text



def test_capabilities_distinguish_available_from_planned_tools():
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["default"] == "deny"
    assert body["policy"]["external_side_effects_require_confirmation"] is True
    assert any(item["id"] == "ollama" for item in body["connectable"])
    planned = {item["id"] for item in body["planned"]}
    assert {"web.search", "windows.worker", "calendar", "device.sync"} <= planned
    assert not any(item["id"] == "web.search" for item in body["available"])


def test_home_page_exposes_czech_browser_voice_controls():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="voiceStart"' in response.text
    assert 'id="voiceStop"' in response.text
    assert 'id="voiceReply"' in response.text
    assert "SpeechRecognition" in response.text
    assert "SpeechSynthesisUtterance" in response.text


def test_home_page_restores_and_clears_persisted_conversation():
    response = client.get("/")
    assert response.status_code == 200
    assert "fetch('/v1/conversations?limit=100')" in response.text
    assert "fetch('/v1/conversations',{method:'DELETE'})" in response.text


def test_tool_registry_is_explicit_and_defaults_to_deny():
    response = client.get("/v1/tools")
    assert response.status_code == 200
    body = response.json()
    assert body["default_policy"] == "deny"
    assert {item["id"] for item in body["tools"]} == {"profile.read", "memory.list", "memory.create"}
    assert next(item for item in body["tools"] if item["id"] == "memory.create")["confirmation_required"] is True


def test_tool_execution_is_allowlisted_and_memory_write_requires_confirmation():
    assert client.post("/v1/tools/profile.read/execute", json={}).status_code == 200
    assert client.post("/v1/tools/shell/execute", json={}).status_code == 404
    denied = client.post("/v1/tools/memory.create/execute", json={"arguments": {"content": "test"}})
    assert denied.status_code == 403
    saved = client.post("/v1/tools/memory.create/execute", json={
        "arguments": {"content": "poznámka z nástroje", "category": "context"}, "confirmed": True
    })
    assert saved.status_code == 200
    assert saved.json()["result"]["content"] == "poznámka z nástroje"
    assert client.get("/v1/memories").json()["memories"][0]["content"] == "poznámka z nástroje"



def test_task_queue_creates_lists_and_cancels():
    created = client.post("/v1/tasks", json={
        "kind": "agent.draft",
        "title": "Připrav plán",
        "input_text": "Připrav krátký plán učení."
    })
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "queued"
    assert client.get("/v1/tasks").json()["tasks"][0]["id"] == task["id"]
    assert client.get(f"/v1/tasks/{task['id']}").json()["title"] == "Připrav plán"
    cancelled = client.post(f"/v1/tasks/{task['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_task_queue_rejects_unapproved_task_kinds_and_unknown_ids():
    invalid = client.post("/v1/tasks", json={
        "kind": "shell.execute", "title": "No", "input_text": "echo unsafe"
    })
    assert invalid.status_code == 422
    assert client.get("/v1/tasks/not-a-real-task").status_code == 404
    assert client.post("/v1/tasks/not-a-real-task/cancel").status_code == 404


def test_worker_processes_one_draft_task(monkeypatch):
    from micro_helper import worker

    created = client.post("/v1/tasks", json={
        "kind": "agent.draft", "title": "Návrh", "input_text": "Napiš krátký návrh."
    })
    task_id = created.json()["id"]

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "Hotový návrh."}}

    monkeypatch.setattr(worker.httpx, "post", lambda *args, **kwargs: FakeResponse())
    assert worker.run_once() is True
    task = client.get(f"/v1/tasks/{task_id}").json()
    assert task["status"] == "completed"
    assert task["result"] == "Hotový návrh."
    assert worker.run_once() is False


def test_worker_marks_task_failed_when_model_is_unavailable(monkeypatch):
    from micro_helper import worker
    import httpx

    created = client.post("/v1/tasks", json={
        "kind": "agent.draft", "title": "Návrh", "input_text": "Napiš návrh."
    })
    task_id = created.json()["id"]

    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(worker.httpx, "post", fail)
    assert worker.run_once() is True
    task = client.get(f"/v1/tasks/{task_id}").json()
    assert task["status"] == "failed"
    assert "offline" in task["error"]



def test_preferences_api_and_ui():
    created = client.post('/v1/preferences', json={'category':'communication','preference':'tone','value':'friendly Czech'})
    assert created.status_code == 201
    assert created.json()['source'] == 'user'
    assert client.get('/v1/preferences').json()['preferences'][0]['value'] == 'friendly Czech'
    assert client.get('/').status_code == 200
    assert 'preferenceForm' in client.get('/').text
    assert client.delete('/v1/preferences/' + str(created.json()['id'])).json()['deleted'] is True



def test_task_queue_ui_is_available():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="taskForm"' in response.text
    assert 'id="taskList"' in response.text
