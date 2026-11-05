from fastapi.testclient import TestClient

import micro_helper.api as api


client = TestClient(api.app)


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
        headers={"origin": "http://testserver"},
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
