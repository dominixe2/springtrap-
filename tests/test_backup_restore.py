import asyncio
import hashlib
import json
import secrets
import uuid
from urllib.parse import urlsplit

import httpx
from fastapi.testclient import TestClient
import pytest

import micro_helper.api as api


raw_client = TestClient(api.app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 8000))


class PolicyAwareTestClient:
    """Simulate the local UI obtaining an exact-action token after approval."""

    def request(self, method, url, **kwargs):
        method = method.upper()
        path = urlsplit(str(url)).path
        if method in {"POST", "PUT", "PATCH", "DELETE"} and path.startswith("/v1/"):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("Origin", "http://127.0.0.1:8000")
            if method == "POST" and path == "/v1/backup/restore":
                payload = kwargs.pop("json", None)
                body_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                digest = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
                confirmation = raw_client.post(
                    "/v1/actions/confirm",
                    json={"method": method, "path": path, "arguments": {"body_sha256": digest}},
                    headers={"Origin": "http://127.0.0.1:8000"},
                )
                if confirmation.status_code == 200:
                    headers["X-Micro-Helper-Confirmation"] = confirmation.json()["confirmation_token"]
                headers.setdefault("Content-Type", "application/json")
                kwargs["content"] = body_text
            elif path not in {"/v1/chat", "/v1/actions/confirm"} and not path.startswith("/v1/tools/"):
                arguments = kwargs.get("json")
                if not isinstance(arguments, dict):
                    arguments = {}
                confirmation = raw_client.post(
                    "/v1/actions/confirm",
                    json={"method": method, "path": path, "arguments": arguments},
                    headers={"Origin": "http://127.0.0.1:8000"},
                )
                if confirmation.status_code == 200:
                    headers["X-Micro-Helper-Confirmation"] = confirmation.json()["confirmation_token"]
            kwargs["headers"] = headers
        return raw_client.request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def __getattr__(self, name):
        return getattr(raw_client, name)


client = PolicyAwareTestClient()


def issue_restore_token(payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    response = raw_client.post(
        "/v1/actions/confirm",
        json={
            "method": "POST",
            "path": "/v1/backup/restore",
            "arguments": {"body_sha256": digest},
        },
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert response.status_code == 200
    return response.json()["confirmation_token"]


STAMP = "2026-11-08T00:00:00+00:00"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "backup-tests.sqlite3")
    raw_client.cookies.clear()
    api._AUTH_LOGIN_FAILURES.clear()
    setup = raw_client.post(
        "/v1/auth/setup",
        json={"password": secrets.token_urlsafe(24)},
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert setup.status_code == 201


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
    response = raw_client.post(
        "/v1/backup/restore",
        json={"backup": valid_backup(), "confirm_replace": False},
        headers={"Origin": "http://127.0.0.1:8000"},
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
    assert 'id="exportBackup"' in html
    assert "body_sha256" in html
    assert "link.download=\"micro-helper-backup.json\"" in html
    assert "window.confirm(" in html
    assert "Stažený JSON soubor není šifrovaný" in html
    assert "Export poznámek vytvoří nešifrovaný JSON" in html


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



def test_restore_rejects_chunked_body_over_limit_without_content_length():
    async def request():
        async def chunks():
            yield b'{"backup":'
            yield b" " * (api.MAX_BACKUP_BYTES + 1)

        transport = httpx.ASGITransport(app=api.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as async_client:
            return await async_client.post(
                "/v1/backup/restore",
                content=chunks(),
                headers={"content-type": "application/json"},
            )

    response = asyncio.run(request())

    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert response.json()["detail"] == "Záloha je příliš velká (maximum 8 MiB)."
    # The outer body-limit middleware can reject before the FastAPI cache
    # middleware runs, so it must set both privacy headers itself.
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_restore_replays_valid_chunked_body_without_content_length():
    backup = valid_backup()
    payload = json.dumps(
        {"backup": backup, "confirm_replace": True},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    token = issue_restore_token(payload)

    async def request():
        async def chunks():
            yield payload[:17]
            yield payload[17:]

        transport = httpx.ASGITransport(app=api.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as async_client:
            return await async_client.post(
                "/v1/backup/restore",
                content=chunks(),
                headers={
                    "content-type": "application/json",
                    "x-micro-helper-confirmation": token,
                },
            )

    response = asyncio.run(request())

    assert "content-length" not in response.request.headers
    assert response.status_code == 200
    assert client.get("/v1/profile").json()["agent_name"] == "Nova"

def test_restore_rolls_back_every_collection_when_database_write_fails():
    seed_existing_data()
    with api.database() as db:
        db.execute(
            "INSERT INTO messages(role, content, created_at) VALUES ('user', 'Původní zpráva', ?)",
            (STAMP,),
        )
        db.execute(
            """
            CREATE TRIGGER fail_restore_memory
            BEFORE INSERT ON memories
            BEGIN
                SELECT RAISE(ABORT, 'simulated restore failure');
            END;
            """
        )
        db.commit()

    response = client.post(
        "/v1/backup/restore",
        json={"backup": valid_backup(), "confirm_replace": True},
    )

    assert response.status_code == 422
    assert client.get("/v1/profile").json()["agent_name"] == "Původní"
    assert [row["content"] for row in client.get("/v1/memories").json()["memories"]] == ["Původní poznámka"]
    assert [row["content"] for row in client.get("/v1/conversations").json()["messages"]] == ["Původní zpráva"]
    assert client.get("/v1/tasks").json()["tasks"][0]["title"] == "Původní úkol"
    assert client.get("/v1/learning-plans").json()["plans"][0]["title"] == "Původní plán"
    assert client.get("/v1/preferences").json()["preferences"][0]["value"] == "yes"


def test_local_ui_uses_micro_helper_as_the_default_identity():
    html = client.get("/").text

    assert 'value="Micro Helper"' in html
    assert "Mykla" not in html
    assert "localStorage.getItem('mh_name')||'Micro Helper'" in html
    assert 'profile:{agent_name:"Micro Helper"' in html



def test_restore_requires_policy_confirmation_even_when_replace_boolean_is_true():
    seed_existing_data()
    response = raw_client.post(
        "/v1/backup/restore",
        json={"backup": valid_backup(), "confirm_replace": True},
    )
    assert response.status_code == 403
    assert client.get("/v1/profile").json()["agent_name"] == "Původní"
    assert client.get("/v1/memories").json()["memories"][0]["content"] == "Původní poznámka"


def test_restore_confirmation_is_bound_to_exact_bytes_and_is_single_use():
    seed_existing_data()
    backup = valid_backup()
    payload = json.dumps(
        {"backup": backup, "confirm_replace": True},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    token = issue_restore_token(payload)
    tampered = valid_backup()
    tampered["profile"]["agent_name"] = "Změněno po potvrzení"
    tampered_payload = json.dumps(
        {"backup": tampered, "confirm_replace": True},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    mismatch = raw_client.post(
        "/v1/backup/restore",
        content=tampered_payload,
        headers={"content-type": "application/json", "origin": "http://127.0.0.1:8000", "x-micro-helper-confirmation": token},
    )
    assert mismatch.status_code == 403
    assert client.get("/v1/profile").json()["agent_name"] == "Původní"

    restored = raw_client.post(
        "/v1/backup/restore",
        content=payload,
        headers={"content-type": "application/json", "origin": "http://127.0.0.1:8000", "x-micro-helper-confirmation": token},
    )
    assert restored.status_code == 200
    replay = raw_client.post(
        "/v1/backup/restore",
        content=payload,
        headers={"content-type": "application/json", "origin": "http://127.0.0.1:8000", "x-micro-helper-confirmation": token},
    )
    assert replay.status_code == 403
    assert client.get("/v1/profile").json()["agent_name"] == "Nova"
