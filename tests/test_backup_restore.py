import uuid

from fastapi.testclient import TestClient
import pytest

import micro_helper.api as api


client = TestClient(api.app, base_url="http://127.0.0.1:8000")
STAMP = "2026-11-08T00:00:00+00:00"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "backup-tests.sqlite3")


def valid_backup():
    return {
        "format": "micro-helper-backup",
        "version": 1,
        "created_at": STAMP,
        "profile": {
            "agent_name": "Nova",
            "language": "cs-CZ",
            "style": "stručný",
            "updated_at": STAMP,
        },
        "memories": [
            {"id": 11, "content": "Zachovej češtinu", "category": "preference", "created_at": STAMP}
        ],
        "messages": [
            {"id": 21, "role": "user", "content": "Ahoj", "created_at": STAMP},
            {"id": 22, "role": "assistant", "content": "Dobrý den.", "created_at": STAMP},
        ],
        "tasks": [
            {
                "id": str(uuid.uuid4()),
                "kind": "agent.draft",
                "title": "Připrav návrh",
                "input_text": "Napiš stručný návrh.",
                "status": "completed",
                "result": "Hotovo.",
                "error": None,
                "created_at": STAMP,
                "updated_at": STAMP,
                "started_at": STAMP,
                "finished_at": STAMP,
            }
        ],
        "learning_plans": [
            {
                "id": str(uuid.uuid4()),
                "title": "Python",
                "goal": "Zvládnout základy",
                "steps": ["Proměnné", "Podmínky"],
                "status": "active",
                "created_at": STAMP,
                "updated_at": STAMP,
            }
        ],
        "preferences": [
            {
                "id": 31,
                "category": "communication",
                "preference": "language",
                "value": "Czech",
                "source": "user",
                "updated_at": STAMP,
            }
        ],
    }


def seed_existing_data():
    client.put("/v1/profile", json={"agent_name": "Původní", "language": "cs-CZ", "style": "friendly"})
    client.post("/v1/memories", json={"content": "Původní poznámka", "category": "context"})
    client.post("/v1/tasks", json={"title": "Původní úkol", "input_text": "Nedotýkat se"})
    client.post("/v1/learning-plans", json={"title": "Původní plán", "goal": "Zachovat", "steps": ["Krok"]})
    client.post("/v1/preferences", json={"category": "other", "preference": "keep", "value": "yes"})


def test_backup_exports_all_persistent_user_collections_without_cache():
    seed_existing_data()
    with api.database() as db:
        db.execute(
            "INSERT INTO messages(role, content, created_at) VALUES ('user', 'Původní zpráva', ?)",
            (STAMP,),
        )
        db.commit()

    response = client.get("/v1/backup")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["format"] == "micro-helper-backup"
    assert payload["version"] == 1
    assert payload["profile"]["agent_name"] == "Původní"
    assert payload["memories"][0]["content"] == "Původní poznámka"
    assert payload["messages"][0]["content"] == "Původní zpráva"
    assert payload["tasks"][0]["title"] == "Původní úkol"
    assert payload["learning_plans"][0]["steps"] == ["Krok"]
    assert payload["preferences"][0]["value"] == "yes"


def test_restore_replaces_all_collections_after_explicit_confirmation():
    seed_existing_data()
    backup = valid_backup()

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 200
    assert response.json()["restored"] == {
        "memories": 1,
        "messages": 2,
        "tasks": 1,
        "learning_plans": 1,
        "preferences": 1,
    }
    assert client.get("/v1/profile").json()["agent_name"] == "Nova"
    assert [row["content"] for row in client.get("/v1/memories").json()["memories"]] == ["Zachovej češtinu"]
    assert [row["content"] for row in client.get("/v1/conversations").json()["messages"]] == ["Ahoj", "Dobrý den."]
    assert client.get("/v1/tasks").json()["tasks"][0]["title"] == "Připrav návrh"
    assert client.get("/v1/learning-plans").json()["plans"][0]["steps"] == ["Proměnné", "Podmínky"]
    assert client.get("/v1/preferences").json()["preferences"][0]["value"] == "Czech"


def test_restore_without_confirmation_does_not_replace_existing_data():
    seed_existing_data()
    response = client.post(
        "/v1/backup/restore",
        json={"backup": valid_backup(), "confirm_replace": False},
    )
    assert response.status_code == 403
    assert client.get("/v1/profile").json()["agent_name"] == "Původní"
    assert client.get("/v1/memories").json()["memories"][0]["content"] == "Původní poznámka"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda backup: backup["memories"].append(dict(backup["memories"][0])),
        lambda backup: backup["memories"][0].update({"id": True}),
        lambda backup: backup["messages"][0].update({"role": "system"}),
        lambda backup: backup["tasks"][0].update({"status": "shell.execute"}),
        lambda backup: backup["learning_plans"][0].update({"steps": []}),
        lambda backup: backup["preferences"].append(dict(backup["preferences"][0])),
    ],
)
def test_invalid_backup_is_rejected_before_existing_data_changes(mutate):
    seed_existing_data()
    backup = valid_backup()
    mutate(backup)

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 422
    assert client.get("/v1/profile").json()["agent_name"] == "Původní"
    assert client.get("/v1/memories").json()["memories"][0]["content"] == "Původní poznámka"
    assert client.get("/v1/tasks").json()["tasks"][0]["title"] == "Původní úkol"
    assert client.get("/v1/learning-plans").json()["plans"][0]["title"] == "Původní plán"
    assert client.get("/v1/preferences").json()["preferences"][0]["value"] == "yes"


def test_backup_controls_are_available_in_the_mobile_friendly_ui():
    html = client.get("/").text
    assert 'id="exportBackup"' in html
    assert 'id="importBackup"' in html
    assert 'id="backupFile"' in html
    assert 'fetch("/v1/backup/restore"' in html
    assert "window.confirm(" in html


def test_restore_requeues_tasks_that_were_running_in_the_backup():
    backup = valid_backup()
    backup["tasks"][0]["status"] = "running"

    response = client.post(
        "/v1/backup/restore",
        json={"backup": backup, "confirm_replace": True},
    )

    assert response.status_code == 200
    assert client.get("/v1/tasks").json()["tasks"][0]["status"] == "queued"


def test_export_refuses_a_backup_larger_than_the_supported_restore_limit(monkeypatch):
    seed_existing_data()
    monkeypatch.setattr(api, "MAX_BACKUP_BYTES", 1)

    response = client.get("/v1/backup")

    assert response.status_code == 413
    assert "8 MiB" in response.json()["detail"]
