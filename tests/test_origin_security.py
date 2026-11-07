from fastapi.testclient import TestClient
import pytest

import micro_helper.api as api


client = TestClient(api.app, base_url="http://127.0.0.1:8000")


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "origin-tests.sqlite3")


def test_cross_origin_profile_write_is_rejected():
    response = client.put(
        "/v1/profile",
        headers={"origin": "https://attacker.example"},
        json={"agent_name": "Changed", "language": "cs-CZ", "style": "friendly"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin write blocked."
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"


def test_cross_site_fetch_metadata_is_rejected_without_origin():
    response = client.post(
        "/v1/memories",
        headers={"sec-fetch-site": "cross-site"},
        json={"content": "must not be saved", "category": "test"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-site request blocked."
    assert client.get("/v1/memories").json()["memories"] == []


def test_same_origin_profile_write_still_works():
    response = client.put(
        "/v1/profile",
        headers={"origin": "http://127.0.0.1:8000"},
        json={"agent_name": "Nova", "language": "cs-CZ", "style": "friendly"},
    )
    assert response.status_code == 200
    assert response.json()["agent_name"] == "Nova"


def test_safe_get_is_not_blocked_only_because_origin_is_external():
    response = client.get(
        "/v1/status",
        headers={"origin": "https://attacker.example", "sec-fetch-site": "cross-site"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/v1/status",
        "/v1/capabilities",
        "/v1/tools",
        "/v1/tasks",
        "/v1/learning-plans",
        "/v1/profile",
        "/v1/memories",
        "/v1/preferences",
        "/v1/conversations",
        "/v1/models",
    ],
)
def test_non_loopback_host_cannot_read_private_api_routes(path):
    response = client.get(
        path,
        headers={
            "host": "localhost.attacker.example:8000",
            "origin": "http://localhost.attacker.example:8000",
            "sec-fetch-site": "same-origin",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Non-loopback host blocked."


def test_non_loopback_host_cannot_submit_chat_or_tool_requests():
    chat = client.post(
        "/v1/chat",
        headers={"host": "attacker.example:8000", "origin": "http://attacker.example:8000"},
        json={"message": "nepovolený požadavek", "model": "llama3.2"},
    )
    tool = client.post(
        "/v1/tools/windows.worker/execute",
        headers={"host": "attacker.example:8000", "origin": "http://attacker.example:8000"},
        json={"action": "notepad"},
    )
    assert chat.status_code == 403
    assert tool.status_code == 403


@pytest.mark.parametrize("origin", ["http://127.0.0.1:9999", "http://user@127.0.0.1:8000", "null"])
def test_malformed_or_wrong_origin_is_rejected(origin):
    response = client.put(
        "/v1/profile",
        headers={"origin": origin},
        json={"agent_name": "Rejected", "language": "cs-CZ", "style": "friendly"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("hostname", ["localhost", "localhost.", "127.0.0.1", "::1"])
def test_loopback_hostname_helper_accepts_localhost(hostname):
    assert api._is_loopback_hostname(hostname) is True


@pytest.mark.parametrize("hostname", ["attacker.example", "192.0.2.10", "0.0.0.0", ""])
def test_loopback_hostname_helper_rejects_non_loopback(hostname):
    assert api._is_loopback_hostname(hostname) is False
