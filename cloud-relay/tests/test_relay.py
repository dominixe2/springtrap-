import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app import app, sessions, tokens, digest, claim_attempts, register_attempts

client = TestClient(app)


def setup_function():
    sessions.clear()
    tokens.clear()
    claim_attempts.clear()
    register_attempts.clear()


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
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/ws") as ws:
            ws.send_json({"type": "auth", "token": "not-a-valid-token"})
            ws.receive_json()


def test_allowlisted_command_routes_between_paired_devices():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = client.post("/v1/pair/claim", json={"pairing_code": "123456"}).json()["token"]
    with client.websocket_connect("/v1/ws") as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        assert desktop.receive_json() == {"type": "ready", "role": "desktop"}
        with client.websocket_connect("/v1/ws") as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            assert mobile.receive_json() == {"type": "ready", "role": "mobile"}
            mobile.send_json({"type": "command", "action": "notepad", "request_id": "req-1"})
            assert desktop.receive_json() == {"type": "command", "action": "notepad", "request_id": "req-1"}
            desktop.send_json({"type": "result", "request_id": "req-1", "ok": True, "message": "Spuštěno"})
            assert mobile.receive_json() == {"type": "result", "request_id": "req-1", "ok": True, "message": "Spuštěno"}


def test_pairing_claims_are_rate_limited():
    assert register().status_code == 200
    for _ in range(8):
        response = client.post("/v1/pair/claim", json={"pairing_code": "999999"})
        assert response.status_code == 404
    response = client.post("/v1/pair/claim", json={"pairing_code": "999999"})
    assert response.status_code == 429


def test_pairing_registration_is_rate_limited():
    for index in range(20):
        response = client.post(
            "/v1/pair/register",
            json={
                "pairing_code": f"{index:06d}",
                "desktop_token": f"d{index:039d}",
            },
        )
        assert response.status_code == 200
    blocked = client.post(
        "/v1/pair/register",
        json={"pairing_code": "999999", "desktop_token": "z" * 40},
    )
    assert blocked.status_code == 429


def test_revoked_token_is_rechecked_before_next_websocket_message():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = client.post(
        "/v1/pair/claim", json={"pairing_code": "123456"}
    ).json()["token"]

    with client.websocket_connect("/v1/ws") as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        assert desktop.receive_json() == {"type": "ready", "role": "desktop"}
        with client.websocket_connect("/v1/ws") as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            assert mobile.receive_json() == {"type": "ready", "role": "mobile"}

            # Simulate revocation after authentication but before the next
            # message. A previously authenticated socket must not stay trusted.
            tokens.pop(digest(mobile_token))
            mobile.send_json({
                "type": "command", "action": "notepad", "request_id": "after-revoke"
            })
            with pytest.raises(WebSocketDisconnect):
                mobile.receive_json()


def test_pending_commands_are_bounded_and_results_must_match():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = client.post(
        "/v1/pair/claim", json={"pairing_code": "123456"}
    ).json()["token"]

    with client.websocket_connect("/v1/ws") as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        assert desktop.receive_json() == {"type": "ready", "role": "desktop"}
        with client.websocket_connect("/v1/ws") as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            assert mobile.receive_json() == {"type": "ready", "role": "mobile"}

            for index in range(20):
                mobile.send_json({
                    "type": "command", "action": "notepad", "request_id": f"req-{index}"
                })

            duplicate = mobile.send_json({
                "type": "command", "action": "notepad", "request_id": "req-0"
            })
            duplicate_error = mobile.receive_json()
            assert duplicate_error["error"] == "duplicate_request_id"

            overflow = mobile.send_json({
                "type": "command", "action": "notepad", "request_id": "req-overflow"
            })
            overflow_error = mobile.receive_json()
            assert overflow_error["error"] == "too_many_pending"

            for index in range(20):
                forwarded = desktop.receive_json()
                assert forwarded["request_id"] == f"req-{index}"

            desktop.send_json({
                "type": "result", "request_id": "not-requested", "ok": True, "message": "ignored"
            })
            unknown = desktop.receive_json()
            assert unknown["error"] == "unknown_request"


def test_mobile_can_revoke_entire_pairing():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = client.post("/v1/pair/claim", json={"pairing_code": "123456"}).json()["token"]
    response = client.post("/v1/pair/revoke", json={"token": mobile_token})
    assert response.status_code == 200
    assert response.json() == {"revoked": True}
    assert not sessions
    assert not tokens
    assert desktop_token not in tokens


def test_browser_pairing_preflight_allows_only_official_origin():
    allowed = client.options(
        "/v1/pair/claim",
        headers={
            "Origin": "https://micro-helper-ygeuyn.v2.appdeploy.ai",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://micro-helper-ygeuyn.v2.appdeploy.ai"
    blocked = client.options(
        "/v1/pair/claim",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert "access-control-allow-origin" not in blocked.headers
