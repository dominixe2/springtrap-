"""Ephemeral, allowlisted WebSocket relay for Micro Helper device pairing.

This is a staging relay: sessions live in memory and disappear on restart/sleep.
No shell commands are accepted or forwarded.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

app = FastAPI(title="Micro Helper Relay", version="0.1.0")
ALLOWED_ACTIONS = {"lock", "explorer", "notepad", "calculator"}
PAIR_TTL = 300
SESSION_TTL = 12 * 60 * 60
MAX_PENDING = 20


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


class RegisterRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=12, pattern=r"^[0-9]{6,12}$")
    desktop_token: str = Field(min_length=32, max_length=200)


class ClaimRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=12, pattern=r"^[0-9]{6,12}$")


def prune() -> None:
    now = time.time()
    expired = []
    for sid, session in sessions.items():
        ttl = SESSION_TTL if session.claimed else PAIR_TTL
        if now - session.created_at > ttl:
            expired.append(sid)
    for sid in expired:
        session = sessions.pop(sid)
        tokens.pop(session.desktop_hash, None)
        if session.mobile_hash:
            tokens.pop(session.mobile_hash, None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "micro-helper-relay", "mode": "ephemeral"}


@app.post("/v1/pair/register")
async def register(body: RegisterRequest) -> dict[str, Any]:
    async with registry_lock:
        prune()
        code_hash = digest(body.pairing_code)
        if any(secrets.compare_digest(s.code_hash, code_hash) for s in sessions.values()):
            raise HTTPException(409, "Pairing code already exists.")
        if len(sessions) >= 1000:
            raise HTTPException(503, "Relay is at capacity.")
        sid = secrets.token_urlsafe(18)
        token_hash = digest(body.desktop_token)
        sessions[sid] = Session(sid, code_hash, token_hash)
        tokens[token_hash] = (sid, "desktop")
        return {"registered": True, "session_id": sid, "expires_in": PAIR_TTL}


@app.post("/v1/pair/claim")
async def claim(body: ClaimRequest, request: Request) -> dict[str, Any]:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = [stamp for stamp in claim_attempts.get(client_ip, []) if now - stamp < 300]
    if len(attempts) >= 8:
        raise HTTPException(429, "Too many pairing attempts. Try again later.")
    attempts.append(now)
    claim_attempts[client_ip] = attempts
    async with registry_lock:
        prune()
        code_hash = digest(body.pairing_code)
        found = next((s for s in sessions.values() if secrets.compare_digest(s.code_hash, code_hash)), None)
        if found is None or found.claimed:
            raise HTTPException(404, "Pairing code is invalid or expired.")
        mobile_token = secrets.token_urlsafe(36)
        found.mobile_hash = digest(mobile_token)
        found.claimed = True
        tokens[found.mobile_hash] = (found.session_id, "mobile")
        return {"paired": True, "session_id": found.session_id, "token": mobile_token, "expires_in": SESSION_TTL}


@app.websocket("/v1/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if origin and origin != "https://micro-helper-ygeuyn.v2.appdeploy.ai":
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    await websocket.accept()
    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except Exception:
        await websocket.close(code=4401, reason="Authentication required")
        return
    token = auth_message.get("token", "") if isinstance(auth_message, dict) and auth_message.get("type") == "auth" else ""
    token_hash = digest(token) if isinstance(token, str) and token else ""
    async with registry_lock:
        prune()
        identity = tokens.get(token_hash)
        session = sessions.get(identity[0]) if identity else None
        role = identity[1] if identity else ""
    if session is None or role not in {"desktop", "mobile"}:
        await websocket.close(code=4401, reason="Invalid or expired relay token")
        return
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
    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                await websocket.send_json({"type": "error", "error": "object_required"})
                continue
            if role == "mobile":
                action = message.get("action")
                request_id = message.get("request_id")
                if message.get("type") != "command" or action not in ALLOWED_ACTIONS:
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
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        async with session.lock:
            if role == "desktop" and session.desktop is websocket:
                session.desktop = None
            if role == "mobile" and session.mobile is websocket:
                session.mobile = None
