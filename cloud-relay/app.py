"""Ephemeral, allowlisted WebSocket relay for Micro Helper device pairing.

This is a staging relay: sessions live in memory and disappear on restart/sleep.
No shell commands are accepted or forwarded.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import os
import re
import secrets
import time
import unicodedata
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

def normalize_allowed_origin(value: str | None) -> str | None:
    """Normalize one explicitly configured HTTPS frontend origin.

    An unset value disables browser pairing instead of silently trusting a
    baked-in hosting provider. Paths, credentials, queries and fragments are
    not origins and are rejected.
    """
    if value is None or not value.strip():
        return None

    raw = value.strip()
    if any(
        character.isspace() or unicodedata.category(character).startswith("C")
        for character in raw
    ):
        raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN must not contain whitespace or control characters.")

    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN must be a valid HTTPS origin.") from error

    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or "?" in raw
        or "#" in raw
    ):
        raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN must contain only an HTTPS origin.")

    if parsed.netloc.endswith(":"):
        raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN contains an empty port.")

    try:
        ascii_host = hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as error:
        raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN contains an invalid hostname.") from error

    try:
        address = ipaddress.ip_address(ascii_host)
    except ValueError:
        if not re.fullmatch(
            r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*",
            ascii_host,
        ):
            raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN contains an invalid hostname.")
        host_part = ascii_host
    else:
        host_part = f"[{address.compressed}]" if address.version == 6 else str(address)

    if port is not None:
        if not 1 <= port <= 65535:
            raise ValueError("MICRO_HELPER_ALLOWED_ORIGIN contains an invalid port.")
        if port != 443:
            host_part = f"{host_part}:{port}"

    return f"https://{host_part}"


APP_ORIGIN = normalize_allowed_origin(os.getenv("MICRO_HELPER_ALLOWED_ORIGIN"))
app = FastAPI(title="Micro Helper Relay", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_ORIGIN] if APP_ORIGIN else [],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class RequestBodyLimitMiddleware:
    """Reject oversized pairing JSON before FastAPI/Pydantic buffers it."""

    def __init__(self, application, max_bytes: int = 8192):
        self.application = application
        self.max_bytes = max_bytes
        self.paths = {"/v1/pair/register", "/v1/pair/claim", "/v1/pair/revoke"}

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST" or scope.get("path") not in self.paths:
            await self.application(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                length = int(declared)
            except (TypeError, ValueError):
                await self._respond(send, 400, "invalid_content_length")
                return
            if length < 0 or length > self.max_bytes:
                await self._respond(send, 413, "request_too_large")
                return

        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                await self._respond(send, 413, "request_too_large")
                return
            body.extend(chunk)
            more_body = message.get("more_body", False)

        replayed = False

        async def replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.application(scope, replay_receive, send)

    @staticmethod
    async def _respond(send, status: int, code: str):
        payload = json.dumps({"error": code}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(payload)).encode("ascii")),
                (b"cache-control", b"no-store"),
                (b"connection", b"close"),
            ],
        })
        await send({"type": "http.response.body", "body": payload, "more_body": False})


app.add_middleware(RequestBodyLimitMiddleware, max_bytes=8192)

ALLOWED_ACTIONS = {"lock", "explorer", "notepad", "calculator"}
PAIR_TTL = 300
SESSION_TTL = 12 * 60 * 60
MAX_PENDING = 20
MAX_SESSIONS = 1000
MAX_RATE_LIMIT_KEYS = 4096
REGISTER_LIMIT = 10
CLAIM_LIMIT = 8
HTTP_RATE_WINDOW = 300
WEBSOCKET_MESSAGE_LIMIT = 120
WEBSOCKET_RATE_WINDOW = 60
MAX_WEBSOCKET_MESSAGE_BYTES = 4096


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class Session:
    session_id: str
    code_hash: str
    desktop_hash: str
    mobile_hash: str = ""
    created_at: float = field(default_factory=time.time)
    claimed: bool = False
    desktop: WebSocket | None = None
    mobile: WebSocket | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


sessions: dict[str, Session] = {}
tokens: dict[str, tuple[str, str]] = {}
registry_lock = asyncio.Lock()
claim_attempts: dict[str, list[float]] = {}
register_attempts: dict[str, list[float]] = {}
websocket_attempts: dict[str, list[float]] = {}


class RegisterRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=12, pattern=r"^[0-9]{6,12}$")
    desktop_token: str = Field(min_length=32, max_length=200)


class ClaimRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=12, pattern=r"^[0-9]{6,12}$")


class RevokeRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)


def consume_rate_limit(
    bucket: dict[str, list[float]],
    key: str,
    limit: int,
    window_seconds: int,
    now: float | None = None,
) -> bool:
    """Bound in-memory rate-limit state and prune expired client keys."""
    current = time.time() if now is None else now
    for old_key, stamps in list(bucket.items()):
        kept = [stamp for stamp in stamps if current - stamp < window_seconds]
        if kept:
            bucket[old_key] = kept
        else:
            bucket.pop(old_key, None)

    attempts = bucket.get(key, [])
    if len(attempts) >= limit:
        return False
    if key not in bucket and len(bucket) >= MAX_RATE_LIMIT_KEYS:
        oldest = min(bucket, key=lambda item: bucket[item][-1] if bucket[item] else 0)
        bucket.pop(oldest, None)
    bucket.setdefault(key, []).append(current)
    return True


def client_key(request: Request) -> str:
    # Do not trust a caller-supplied X-Forwarded-For value for rate limiting.
    return request.client.host if request.client and request.client.host else "unknown"


def browser_origin_allowed(origin: str | None) -> bool:
    """Allow browser pairing only for the explicitly configured frontend origin."""
    return APP_ORIGIN is not None and origin == APP_ORIGIN


def require_browser_origin(request: Request) -> None:
    if APP_ORIGIN is None:
        raise HTTPException(503, "Browser pairing is not configured on this relay.")
    origin = request.headers.get("origin")
    fetch_site = request.headers.get("sec-fetch-site", "").lower()
    if not browser_origin_allowed(origin) or fetch_site == "cross-site":
        raise HTTPException(403, "Požadavek musí pocházet z oficiální aplikace Micro Helper.")


def prune_locked() -> list[WebSocket]:
    """Remove expired sessions while registry_lock is held and return their sockets."""
    now = time.time()
    expired_ids = []
    for session_id, session in list(sessions.items()):
        ttl = SESSION_TTL if session.claimed else PAIR_TTL
        if now - session.created_at > ttl:
            expired_ids.append(session_id)

    peers: list[WebSocket] = []
    for session_id in expired_ids:
        session = sessions.pop(session_id, None)
        if session is None:
            continue
        tokens.pop(session.desktop_hash, None)
        if session.mobile_hash:
            tokens.pop(session.mobile_hash, None)
        peers.extend(peer for peer in (session.desktop, session.mobile) if peer is not None)
        websocket_attempts.pop(session_id + ":desktop", None)
        websocket_attempts.pop(session_id + ":mobile", None)
    return peers


async def close_sockets(peers: list[WebSocket], reason: str) -> None:
    for peer in peers:
        try:
            await peer.close(code=4401, reason=reason)
        except Exception:
            pass


async def session_is_active(
    session: Session,
    token_hash: str,
    role: str,
    websocket: WebSocket,
) -> bool:
    async with registry_lock:
        expired_peers = prune_locked()
        current = sessions.get(session.session_id)
        identity = tokens.get(token_hash)
        active_peer = session.desktop if role == "desktop" else session.mobile
        valid = (
            current is session
            and identity == (session.session_id, role)
            and active_peer is websocket
        )
    await close_sockets(expired_peers, "Pairing expired")
    return valid


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "micro-helper-relay", "mode": "ephemeral"}


@app.post("/v1/pair/register")
async def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    if not consume_rate_limit(register_attempts, client_key(request), REGISTER_LIMIT, HTTP_RATE_WINDOW):
        raise HTTPException(429, "Too many registration attempts. Try again later.")

    expired_peers: list[WebSocket] = []
    result: dict[str, Any] | None = None
    error: tuple[int, str] | None = None
    async with registry_lock:
        expired_peers = prune_locked()
        code_hash = digest(body.pairing_code)
        if any(secrets.compare_digest(s.code_hash, code_hash) for s in sessions.values()):
            error = (409, "Pairing code already exists.")
        elif sum(not session.claimed for session in sessions.values()) >= MAX_PENDING:
            error = (503, "Relay has too many pending pairings.")
        elif len(sessions) >= MAX_SESSIONS:
            error = (503, "Relay is at capacity.")
        else:
            session_id = secrets.token_urlsafe(18)
            token_hash = digest(body.desktop_token)
            sessions[session_id] = Session(session_id, code_hash, token_hash)
            tokens[token_hash] = (session_id, "desktop")
            result = {"registered": True, "session_id": session_id, "expires_in": PAIR_TTL}
    await close_sockets(expired_peers, "Pairing expired")
    if error:
        raise HTTPException(error[0], error[1])
    return result or {"registered": False}


@app.post("/v1/pair/claim")
async def claim(body: ClaimRequest, request: Request) -> dict[str, Any]:
    require_browser_origin(request)
    if not consume_rate_limit(claim_attempts, client_key(request), CLAIM_LIMIT, HTTP_RATE_WINDOW):
        raise HTTPException(429, "Too many pairing attempts. Try again later.")

    expired_peers: list[WebSocket] = []
    result: dict[str, Any] | None = None
    async with registry_lock:
        expired_peers = prune_locked()
        code_hash = digest(body.pairing_code)
        found = next(
            (session for session in sessions.values() if secrets.compare_digest(session.code_hash, code_hash)),
            None,
        )
        if found is not None and not found.claimed:
            mobile_token = secrets.token_urlsafe(36)
            found.mobile_hash = digest(mobile_token)
            found.claimed = True
            found.created_at = time.time()
            tokens[found.mobile_hash] = (found.session_id, "mobile")
            result = {
                "paired": True,
                "session_id": found.session_id,
                "token": mobile_token,
                "expires_in": SESSION_TTL,
            }
    await close_sockets(expired_peers, "Pairing expired")
    if result is None:
        raise HTTPException(404, "Pairing code is invalid or expired.")
    return result


@app.post("/v1/pair/revoke")
async def revoke(body: RevokeRequest, request: Request) -> dict[str, bool]:
    require_browser_origin(request)
    token_hash = digest(body.token)
    async with registry_lock:
        identity = tokens.get(token_hash)
        if identity is None:
            return {"revoked": False}
        session = sessions.pop(identity[0], None)
        if session is None:
            tokens.pop(token_hash, None)
            return {"revoked": False}
        tokens.pop(session.desktop_hash, None)
        if session.mobile_hash:
            tokens.pop(session.mobile_hash, None)
        websocket_attempts.pop(session.session_id + ":desktop", None)
        websocket_attempts.pop(session.session_id + ":mobile", None)
        peers = [peer for peer in (session.desktop, session.mobile) if peer is not None]
    await close_sockets(peers, "Pairing revoked")
    return {"revoked": True}


@app.websocket("/v1/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if origin is not None and not browser_origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not allowed")
        return

    await websocket.accept()
    try:
        auth_event = await asyncio.wait_for(websocket.receive(), timeout=10)
    except Exception:
        await websocket.close(code=4401, reason="Authentication required")
        return

    if auth_event.get("type") == "websocket.disconnect":
        return
    if auth_event.get("type") != "websocket.receive":
        await websocket.close(code=4401, reason="Authentication required")
        return

    auth_text = auth_event.get("text")
    auth_binary = auth_event.get("bytes")
    auth_size = len(auth_text.encode("utf-8")) if isinstance(auth_text, str) else (
        len(auth_binary) if isinstance(auth_binary, bytes) else 0
    )
    if auth_size > MAX_WEBSOCKET_MESSAGE_BYTES:
        await websocket.close(code=1009, reason="Authentication message too large")
        return
    if not isinstance(auth_text, str):
        await websocket.close(code=4401, reason="Text authentication required")
        return
    try:
        auth_message = json.loads(auth_text)
    except json.JSONDecodeError:
        await websocket.close(code=4401, reason="Invalid authentication message")
        return

    token = auth_message.get("token", "") if isinstance(auth_message, dict) and auth_message.get("type") == "auth" else ""
    token_hash = digest(token) if isinstance(token, str) and token else ""
    expired_peers: list[WebSocket] = []
    async with registry_lock:
        expired_peers = prune_locked()
        identity = tokens.get(token_hash)
        session = sessions.get(identity[0]) if identity else None
        role = identity[1] if identity else ""
        valid = session is not None and role in {"desktop", "mobile"}
    await close_sockets(expired_peers, "Pairing expired")

    if not valid or session is None:
        await websocket.close(code=4401, reason="Invalid or expired relay token")
        return
    # The mobile endpoint is browser-only. The desktop companion is a native
    # client and may omit Origin, but any Origin it sends must be official.
    if role == "mobile" and not browser_origin_allowed(origin):
        await websocket.close(code=4403, reason="Browser origin required")
        return

    await websocket.send_json({"type": "ready", "role": role})
    async with session.lock:
        if role == "desktop":
            old, session.desktop = session.desktop, websocket
        else:
            old, session.mobile = session.mobile, websocket
    if old is not None:
        try:
            await old.close(code=4001, reason="Reconnected on another socket")
        except Exception:
            pass

    if not await session_is_active(session, token_hash, role, websocket):
        await websocket.close(code=4401, reason="Pairing expired or revoked")
        return

    try:
        while True:
            event = await websocket.receive()
            if event.get("type") == "websocket.disconnect":
                break
            raw = event.get("text")
            if raw is None:
                binary = event.get("bytes")
                if binary is None:
                    await websocket.send_json({"type": "error", "error": "text_or_json_required"})
                    continue
                if len(binary) > MAX_WEBSOCKET_MESSAGE_BYTES:
                    await websocket.close(code=1009, reason="Message too large")
                    break
                try:
                    raw = binary.decode("utf-8")
                except UnicodeDecodeError:
                    await websocket.send_json({"type": "error", "error": "invalid_utf8"})
                    continue
            if len(raw.encode("utf-8")) > MAX_WEBSOCKET_MESSAGE_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                break

            if not await session_is_active(session, token_hash, role, websocket):
                await websocket.close(code=4401, reason="Pairing expired or revoked")
                break
            if not consume_rate_limit(
                websocket_attempts,
                session.session_id + ":" + role,
                WEBSOCKET_MESSAGE_LIMIT,
                WEBSOCKET_RATE_WINDOW,
            ):
                await websocket.send_json({"type": "error", "error": "rate_limited"})
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "invalid_json"})
                continue
            if not isinstance(message, dict):
                await websocket.send_json({"type": "error", "error": "object_required"})
                continue

            if role == "mobile":
                action = message.get("action")
                request_id = message.get("request_id")
                if message.get("type") != "command" or not isinstance(action, str) or action not in ALLOWED_ACTIONS:
                    await websocket.send_json({"type": "error", "error": "action_not_allowed"})
                    continue
                if not isinstance(request_id, str) or not (1 <= len(request_id) <= 80):
                    await websocket.send_json({"type": "error", "error": "invalid_request_id"})
                    continue
                desktop = session.desktop
                if desktop is None:
                    await websocket.send_json({"type": "error", "request_id": request_id, "error": "desktop_offline"})
                    continue
                await desktop.send_json({"type": "command", "action": action, "request_id": request_id})
            else:
                if message.get("type") != "result":
                    await websocket.send_json({"type": "error", "error": "message_not_allowed"})
                    continue
                request_id = message.get("request_id")
                if not isinstance(request_id, str) or not (1 <= len(request_id) <= 80):
                    continue
                mobile = session.mobile
                if mobile is not None:
                    await mobile.send_json({
                        "type": "result",
                        "request_id": request_id,
                        "ok": bool(message.get("ok")),
                        "message": str(message.get("message", ""))[:240],
                    })
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011, reason="Relay error")
        except Exception:
            pass
    finally:
        async with session.lock:
            if role == "desktop" and session.desktop is websocket:
                session.desktop = None
            if role == "mobile" and session.mobile is websocket:
                session.mobile = None
