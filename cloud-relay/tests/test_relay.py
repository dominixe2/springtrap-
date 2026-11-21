import json
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app as relay
from app import (
    APP_ORIGIN,
    app,
    claim_attempts,
    digest,
    register_attempts,
    sessions,
    tokens,
    websocket_attempts,
)

client = TestClient(app)


def setup_function():
    sessions.clear()
    tokens.clear()
    claim_attempts.clear()
    register_attempts.clear()
    websocket_attempts.clear()


def register(code="123456", token="d" * 40):
    return client.post(
        "/v1/pair/register",
        json={"pairing_code": code, "desktop_token": token},
    )


def claim(code="123456", origin=APP_ORIGIN):
    headers = {"Origin": origin} if origin is not None else {}
    return client.post("/v1/pair/claim", json={"pairing_code": code}, headers=headers)


def revoke(token, origin=APP_ORIGIN):
    headers = {"Origin": origin} if origin is not None else {}
    return client.post("/v1/pair/revoke", json={"token": token}, headers=headers)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "ephemeral"


def test_pairing_code_is_claimed_once_and_token_is_issued():
    assert register().status_code == 200
    claimed = claim()
    assert claimed.status_code == 200
    body = claimed.json()
    assert body["paired"] is True
    assert len(body["token"]) >= 40
    assert claim().status_code == 404


def test_invalid_code_does_not_pair():
    assert register().status_code == 200
    assert claim("999999").status_code == 404


def test_duplicate_active_code_is_rejected():
    assert register().status_code == 200
    assert register().status_code == 409


def test_invalid_pairing_code_shape_is_rejected():
    response = client.post(
        "/v1/pair/register",
        json={"pairing_code": "abc", "desktop_token": "d" * 40},
    )
    assert response.status_code == 422


def test_pairing_http_body_limit_counts_utf8_bytes():
    body = json.dumps({
        "pairing_code": "123456",
        "desktop_token": "d" * 40,
        "padding": "é" * 5000,
    }).encode("utf-8")
    assert len(body) > 8192
    response = client.post(
        "/v1/pair/register",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_mobile_cannot_claim_twice():
    assert register().status_code == 200
    assert claim().status_code == 200
    assert claim().status_code == 404


def test_claim_requires_the_exact_official_origin():
    assert register().status_code == 200
    assert claim(origin=None).status_code == 403
    assert claim(origin="https://attacker.example").status_code == 403
    assert claim().status_code == 200


def test_revoke_requires_the_exact_official_origin():
    assert register().status_code == 200
    mobile_token = claim().json()["token"]
    assert revoke(mobile_token, origin=None).status_code == 403
    assert revoke(mobile_token, origin="https://attacker.example").status_code == 403
    assert revoke(mobile_token).json() == {"revoked": True}


def test_websocket_rejects_unknown_token():
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as ws:
            ws.send_json({"type": "auth", "token": "not-a-valid-token"})
            ws.receive_json()


def test_mobile_websocket_requires_the_official_origin():
    assert register().status_code == 200
    mobile_token = claim().json()["token"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/ws", headers={"origin": "https://attacker.example"}) as ws:
            ws.send_json({"type": "auth", "token": mobile_token})
            ws.receive_json()


def test_allowlisted_command_routes_between_paired_devices():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = claim().json()["token"]
    with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        assert desktop.receive_json() == {"type": "ready", "role": "desktop"}
        with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            assert mobile.receive_json() == {"type": "ready", "role": "mobile"}
            mobile.send_json({"type": "command", "action": "notepad", "request_id": "req-1"})
            assert desktop.receive_json() == {"type": "command", "action": "notepad", "request_id": "req-1"}
            desktop.send_json({"type": "result", "request_id": "req-1", "ok": True, "message": "Spuštěno"})
            assert mobile.receive_json() == {"type": "result", "request_id": "req-1", "ok": True, "message": "Spuštěno"}


def test_pairing_claims_are_rate_limited():
    assert register().status_code == 200
    for _ in range(8):
        response = claim("999999")
        assert response.status_code == 404
    assert claim("999999").status_code == 429


def test_registration_is_rate_limited():
    for index in range(relay.REGISTER_LIMIT):
        code = f"{index:06d}"
        token = "d" * 39 + str(index)
        assert register(code, token).status_code == 200
    assert register("999998", "z" * 40).status_code == 429


def test_pending_pairing_capacity_is_enforced(monkeypatch):
    monkeypatch.setattr(relay, "MAX_PENDING", 1)
    assert register("123456", "d" * 40).status_code == 200
    assert register("123457", "e" * 40).status_code == 503


def test_mobile_can_revoke_entire_pairing():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = claim().json()["token"]
    response = revoke(mobile_token)
    assert response.status_code == 200
    assert response.json() == {"revoked": True}
    assert not sessions
    assert not tokens
    assert digest(desktop_token) not in tokens


def test_revoke_closes_both_active_websockets():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = claim().json()["token"]
    with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        desktop.receive_json()
        with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            mobile.receive_json()
            response = revoke(mobile_token)
            assert response.status_code == 200
            with pytest.raises(WebSocketDisconnect):
                mobile.receive_json()
            with pytest.raises(WebSocketDisconnect):
                desktop.receive_json()


def test_expired_active_websocket_is_closed_before_forwarding():
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = claim().json()["token"]
    with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        assert desktop.receive_json()["role"] == "desktop"
        with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            assert mobile.receive_json()["role"] == "mobile"
            session = next(iter(sessions.values()))
            session.created_at = time.time() - relay.SESSION_TTL - 1
            mobile.send_json({"type": "command", "action": "notepad", "request_id": "expired"})
            with pytest.raises(WebSocketDisconnect):
                mobile.receive_json()
    assert not sessions
    assert not tokens


def test_websocket_messages_are_rate_limited(monkeypatch):
    monkeypatch.setattr(relay, "WEBSOCKET_MESSAGE_LIMIT", 1)
    assert register().status_code == 200
    desktop_token = "d" * 40
    mobile_token = claim().json()["token"]
    with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        desktop.receive_json()
        with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as mobile:
            mobile.send_json({"type": "auth", "token": mobile_token})
            mobile.receive_json()
            mobile.send_json({"type": "command", "action": "notepad", "request_id": "first"})
            assert desktop.receive_json()["request_id"] == "first"
            mobile.send_json({"type": "command", "action": "notepad", "request_id": "second"})
            assert mobile.receive_json() == {"type": "error", "error": "rate_limited"}


def test_websocket_rejects_oversized_messages():
    assert register().status_code == 200
    desktop_token = "d" * 40
    with client.websocket_connect("/v1/ws", headers={"origin": APP_ORIGIN}) as desktop:
        desktop.send_json({"type": "auth", "token": desktop_token})
        desktop.receive_json()
        desktop.send_text("x" * (relay.MAX_WEBSOCKET_MESSAGE_BYTES + 1))
        with pytest.raises(WebSocketDisconnect):
            desktop.receive_json()


def test_rate_limit_prunes_expired_client_keys():
    bucket = {"old-client": [1.0, 2.0]}
    assert relay.consume_rate_limit(bucket, "new-client", 1, 10, now=20.0)
    assert "old-client" not in bucket
    assert bucket["new-client"] == [20.0]


def test_browser_pairing_preflight_allows_only_official_origin():
    allowed = client.options(
        "/v1/pair/claim",
        headers={
            "Origin": APP_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == APP_ORIGIN
    blocked = client.options(
        "/v1/pair/claim",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert "access-control-allow-origin" not in blocked.headers
