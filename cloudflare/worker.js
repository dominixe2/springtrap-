const APP_ORIGIN = "https://micro-helper-ygeuyn.v2.appdeploy.ai";
const ALLOWED_ACTIONS = new Set(["lock", "explorer", "notepad", "calculator"]);
const PAIR_TTL_MS = 5 * 60 * 1000;
const SESSION_TTL_MS = 12 * 60 * 60 * 1000;
const MAX_WEBSOCKET_MESSAGE_BYTES = 4096;

function json(data, status = 200, origin = null) {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "content-type",
    "vary": "Origin",
  };
  if (origin === APP_ORIGIN) headers["access-control-allow-origin"] = APP_ORIGIN;
  return new Response(JSON.stringify(data), { status, headers });
}

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function randomToken(bytes = 36) {
  const data = crypto.getRandomValues(new Uint8Array(bytes));
  let binary = "";
  for (const byte of data) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin");
    if (request.method === "OPTIONS") {
      if (origin !== APP_ORIGIN) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: {
        "access-control-allow-origin": APP_ORIGIN,
        "access-control-allow-methods": "GET, POST, OPTIONS",
        "access-control-allow-headers": "content-type",
        "access-control-max-age": "600",
        "vary": "Origin",
      }});
    }
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET") {
      return json({ status: "ok", service: "micro-helper-cloudflare-relay", mode: "durable-object" }, 200, origin);
    }
    const id = env.RELAY_HUB.idFromName("micro-helper-global-relay");
    return env.RELAY_HUB.get(id).fetch(request);
  },
};

export class RelayHub {
  constructor(state) {
    this.state = state;
    this.sockets = new Map();
  }

  async fetch(request) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    if (origin && origin !== APP_ORIGIN) return json({ error: "origin_not_allowed" }, 403, origin);

    if (url.pathname === "/v1/pair/register" && request.method === "POST") {
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      if (!(await this.rateLimit("register:" + ip, 10, 5 * 60 * 1000))) {
        return json({ error: "rate_limited" }, 429, origin);
      }
      let body;
      try { body = await request.json(); } catch { return json({ error: "invalid_json" }, 400, origin); }
      if (!/^\d{6}$/.test(body.pairing_code || "") || typeof body.desktop_token !== "string" || body.desktop_token.length < 32 || body.desktop_token.length > 200) {
        return json({ error: "invalid_payload" }, 422, origin);
      }
      const codeHash = await sha256(body.pairing_code);
      const sessionId = randomToken(18);
      const desktopHash = await sha256(body.desktop_token);
      const now = Date.now();
      const registered = await this.state.storage.transaction(async (txn) => {
        const existing = await txn.get("code:" + codeHash);
        if (existing && existing.expiresAt > now) return false;
        const session = { sessionId, codeHash, desktopHash, mobileHash: null, claimed: false, createdAt: now, expiresAt: now + PAIR_TTL_MS };
        await txn.put("session:" + sessionId, session);
        await txn.put("code:" + codeHash, { sessionId, expiresAt: session.expiresAt });
        await txn.put("token:" + desktopHash, { sessionId, role: "desktop" });
        return true;
      });
      if (!registered) return json({ error: "code_conflict" }, 409, origin);
      return json({ registered: true, session_id: sessionId, expires_in: 300 }, 200, origin);
    }

    if (url.pathname === "/v1/pair/claim" && request.method === "POST") {
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      if (!(await this.rateLimit("claim:" + ip, 8, 5 * 60 * 1000))) {
        return json({ error: "rate_limited" }, 429, origin);
      }
      let body;
      try { body = await request.json(); } catch { return json({ error: "invalid_json" }, 400, origin); }
      if (!/^\d{6}$/.test(body.pairing_code || "")) return json({ error: "invalid_payload" }, 422, origin);
      const codeHash = await sha256(body.pairing_code);
      const token = randomToken(48);
      const mobileHash = await sha256(token);
      const now = Date.now();
      const claimed = await this.state.storage.transaction(async (txn) => {
        const code = await txn.get("code:" + codeHash);
        if (!code || code.expiresAt <= now) return null;
        const session = await txn.get("session:" + code.sessionId);
        if (!session || session.claimed || session.expiresAt <= now) return null;
        session.mobileHash = mobileHash;
        session.claimed = true;
        session.expiresAt = now + SESSION_TTL_MS;
        await txn.put("session:" + session.sessionId, session);
        await txn.put("token:" + mobileHash, { sessionId: session.sessionId, role: "mobile" });
        await txn.delete("code:" + codeHash);
        return session.sessionId;
      });
      if (!claimed) return json({ error: "invalid_or_expired_code" }, 404, origin);
      return json({ paired: true, session_id: claimed, token, expires_in: 43200 }, 200, origin);
    }

    if (url.pathname === "/v1/pair/revoke" && request.method === "POST") {
      let body;
      try { body = await request.json(); } catch { return json({ error: "invalid_json" }, 400, origin); }
      if (typeof body.token !== "string" || body.token.length < 32 || body.token.length > 200) return json({ error: "invalid_payload" }, 422, origin);
      const tokenHash = await sha256(body.token);
      const identity = await this.state.storage.get("token:" + tokenHash);
      if (!identity) return json({ revoked: false }, 200, origin);
      const session = await this.state.storage.get("session:" + identity.sessionId);
      if (session) {
        await this.state.storage.delete("token:" + session.desktopHash);
        if (session.mobileHash) await this.state.storage.delete("token:" + session.mobileHash);
        if (session.codeHash) await this.state.storage.delete("code:" + session.codeHash);
        await this.state.storage.delete("session:" + session.sessionId);
      }
      for (const socket of this.state.getWebSockets()) {
        const attachment = socket.deserializeAttachment();
        if (attachment?.sessionId === identity.sessionId) {
          try { socket.close(4401, "Pairing revoked"); } catch {}
        }
      }
      return json({ revoked: true }, 200, origin);
    }

    if (url.pathname === "/v1/ws") return this.handleWebSocket(request);
    return json({ error: "not_found" }, 404, origin);
  }

  async rateLimit(key, limit, windowMs) {
    const now = Date.now();
    const record = await this.state.storage.get("rate:" + key) || { hits: [] };
    record.hits = record.hits.filter((stamp) => now - stamp < windowMs);
    if (record.hits.length >= limit) {
      await this.state.storage.put("rate:" + key, record, { expirationTtl: Math.ceil(windowMs / 1000) });
      return false;
    }
    record.hits.push(now);
    await this.state.storage.put("rate:" + key, record, { expirationTtl: Math.ceil(windowMs / 1000) });
    return true;
  }

  async handleWebSocket(request) {
    if (request.headers.get("Upgrade")?.toLowerCase() !== "websocket") return new Response("WebSocket upgrade required", { status: 426 });
    const pair = new WebSocketPair();
    const client = pair[0];
    const server = pair[1];
    // Use the Durable Object WebSocket API so sockets survive hibernation
    // and can be enumerated/closed during pairing revocation.
    this.state.acceptWebSocket(server);
    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(server, rawMessage) {
    let message;
    try {
      const raw = typeof rawMessage === "string" ? rawMessage : new TextDecoder().decode(rawMessage);
      if (new TextEncoder().encode(raw).byteLength > MAX_WEBSOCKET_MESSAGE_BYTES) {
        server.close(1009, "Message too large");
        return;
      }
      message = JSON.parse(raw);
    } catch {
      try { server.send(JSON.stringify({ type: "error", error: "invalid_json" })); } catch {}
      return;
    }

    let attachment = server.deserializeAttachment();
    if (!attachment) {
      if (message?.type !== "auth" || typeof message.token !== "string" || message.token.length < 32 || message.token.length > 200) {
        server.close(4401, "Authentication required");
        return;
      }
      const tokenHash = await sha256(message.token);
      const identity = await this.state.storage.get("token:" + tokenHash);
      const session = identity ? await this.state.storage.get("session:" + identity.sessionId) : null;
      if (!identity || !session || session.expiresAt <= Date.now()) {
        server.close(4401, "Invalid or expired relay token");
        return;
      }
      attachment = { sessionId: identity.sessionId, role: identity.role };
      server.serializeAttachment(attachment);
      server.send(JSON.stringify({ type: "ready", role: identity.role }));
      return;
    }

    // A socket must not outlive its pairing: check storage on every message so
    // expiry and revocation apply to already-authenticated, hibernated sockets.
    const session = await this.state.storage.get("session:" + attachment.sessionId);
    if (!session || session.expiresAt <= Date.now()) {
      server.close(4401, "Pairing expired or revoked");
      return;
    }

    // Bound command/result traffic per paired device role, including reconnects.
    if (!(await this.rateLimit("websocket:" + attachment.sessionId + ":" + attachment.role, 120, 60 * 1000))) {
      try { server.send(JSON.stringify({ type: "error", error: "rate_limited" })); } catch {}
      return;
    }

    if (attachment.role === "mobile") {
      if (message?.type !== "command" || !ALLOWED_ACTIONS.has(message.action) || typeof message.request_id !== "string" || message.request_id.length < 1 || message.request_id.length > 80) {
        server.send(JSON.stringify({ type: "error", error: "action_not_allowed" }));
        return;
      }
      const peer = this.findPeer(attachment.sessionId, "desktop");
      if (!peer) {
        server.send(JSON.stringify({ type: "error", request_id: message.request_id, error: "desktop_offline" }));
        return;
      }
      peer.send(JSON.stringify({ type: "command", action: message.action, request_id: message.request_id }));
      return;
    }

    if (attachment.role === "desktop") {
      if (message?.type !== "result" || typeof message.request_id !== "string" || message.request_id.length < 1 || message.request_id.length > 80) {
        server.send(JSON.stringify({ type: "error", error: "message_not_allowed" }));
        return;
      }
      const peer = this.findPeer(attachment.sessionId, "mobile");
      if (peer) peer.send(JSON.stringify({ type: "result", request_id: message.request_id, ok: Boolean(message.ok), message: String(message.message || "").slice(0, 240) }));
      return;
    }

    server.close(4403, "Unknown relay role");
  }

  webSocketClose(_server, _code, _reason, _wasClean) {}
  webSocketError(_server, _error) {}

  findPeer(sessionId, role) {
    for (const socket of this.state.getWebSockets()) {
      try {
        const attachment = socket.deserializeAttachment();
        if (attachment?.sessionId === sessionId && attachment?.role === role && socket.readyState === WebSocket.OPEN) return socket;
      } catch {}
    }
    return null;
  }
}
