from fastapi.testclient import TestClient
import pytest

import micro_helper.api as api


client = TestClient(api.app, base_url="http://127.0.0.1:8000")


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "origin-tests.sqlite3")


def test_cross_origin_profile_write_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "origin-test.sqlite3")

    response = client.put(
        "/v1/profile",
        headers={"origin": "https://attacker.example"},
        json={"agent_name": "Changed", "language": "cs-CZ", "style": "friendly"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin write blocked."
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"


def test_cross_site_fetch_metadata_is_rejected_even_without_origin():
    response = client.post(
        "/v1/memories",
        headers={"sec-fetch-site": "cross-site"},
        json={"content": "must not be saved", "category": "test"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-site request blocked."
    assert client.get("/v1/memories").json()["memories"] == []


def test_same_origin_profile_write_still_works(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE_PATH", tmp_path / "same-origin.sqlite3")

    response = client.put(
        "/v1/profile",
        headers={"origin": "http://127.0.0.1:8000"},
        json={"agent_name": "Nova", "language": "cs-CZ", "style": "friendly"},
    )

    assert response.status_code == 200
    assert response.json()["agent_name"] == "Nova"


def test_origin_guard_does_not_block_safe_get_requests():
    response = client.get(
        "/v1/status",
        headers={"origin": "https://attacker.example", "sec-fetch-site": "cross-site"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize("origin", ["http://testserver:9999", "http://user@testserver"])
def test_profile_write_rejects_origin_with_wrong_port_or_userinfo(origin):
    response = client.put(
        "/v1/profile",
        headers={"origin": origin},
        json={"agent_name": "Rejected", "language": "cs-CZ", "style": "friendly"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin write blocked."
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"

@pytest.mark.parametrize("host", ["attacker.example:8000", "192.0.2.10:8000"])
def test_profile_write_rejects_non_loopback_host_even_when_origin_matches(host):
    response = client.put(
        "/v1/profile",
        headers={
            "host": host,
            "origin": f"http://{host}",
            "sec-fetch-site": "same-origin",
        },
        json={"agent_name": "Rejected", "language": "cs-CZ", "style": "friendly"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Non-loopback host blocked."
    assert client.get("/v1/profile").json()["agent_name"] == "Mykla"


def test_non_loopback_host_cannot_read_private_api_backup():
    response = client.get(
        "/v1/backup",
        headers={
            "host": "attacker.example:8000",
            "origin": "http://attacker.example:8000",
            "sec-fetch-site": "same-origin",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Non-loopback host blocked."


@pytest.mark.parametrize("origin", ["http://[", "http://127.0.0.1:8000/path", "null"])
def test_malformed_or_non_origin_value_is_rejected_for_writes(origin):
    response = client.put(
        "/v1/profile",
        headers={"origin": origin},
        json={"agent_name": "Rejected", "language": "cs-CZ", "style": "friendly"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin write blocked."

