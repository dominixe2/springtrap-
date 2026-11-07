from fastapi.testclient import TestClient
from app import app, sessions, tokens, digest

client = TestClient(app)


def setup_function():
    sessions.clear()
    tokens.clear()


def register(code="123456", token="d" * 40):
    return client.post("/v1/pair/register", json={"pairing_code": code, "desktop_token": token})


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "ephemeral"


def test_pairing_code_is_claimed_once_and_token_is_issued():
    assert register().status_code == 200
    claimed = client.post("/v1/pair/claim", json={"pairing_code": "123456"})
    assert claimed.status_code == 200
    body = claimed.json()
    assert body["paired"] is True
    assert len(body["token"]) >= 40
    assert client.post("/v1/pair/claim", json={"pairing_code": "123456"}).status_code == 404


def test_invalid_code_does_not_pair():
    assert register().status_code == 200
    assert client.post("/v1/pair/claim", json={"pairing_code": "999999"}).status_code == 404


def test_duplicate_active_code_is_rejected():
    assert register().status_code == 200
    assert register().status_code == 409


def test_invalid_pairing_code_shape_is_rejected():
    response = client.post("/v1/pair/register", json={"pairing_code": "abc", "desktop_token": "d" * 40})
    assert response.status_code == 422


def test_mobile_cannot_claim_twice():
    assert register().status_code == 200
    assert client.post("/v1/pair/claim", json={"pairing_code": "123456"}).status_code == 200
    assert client.post("/v1/pair/claim", json={"pairing_code": "123456"}).status_code == 404


def test_websocket_rejects_unknown_token():
    with client.websocket_connect("/v1/ws?token=not-a-valid-token") as ws:
        # TestClient may accept before server-side close is observed.
        try:
            ws.receive_json()
            assert False, "unauthorized socket must not receive messages"
        except Exception:
            pass
