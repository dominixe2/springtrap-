import assert from "node:assert/strict";
import test from "node:test";

import { RelayHub } from "../worker.js";

function makeState(entries = {}) {
  const values = new Map(Object.entries(entries));
  return {
    values,
    storage: {
      get: async (key) => values.get(key),
      put: async (key, value) => { values.set(key, value); },
      delete: async (key) => values.delete(key),
    },
    getWebSockets: () => [],
  };
}

function makeSocket(attachment) {
  return {
    sent: [],
    closed: [],
    deserializeAttachment: () => attachment,
    serializeAttachment: (value) => { attachment = value; },
    send(raw) { this.sent.push(JSON.parse(raw)); },
    close(code, reason) { this.closed.push({ code, reason }); },
  };
}

test("an expired pairing closes an already-authenticated websocket", async () => {
  const state = makeState({
    "session:expired": { sessionId: "expired", expiresAt: Date.now() - 1 },
  });
  const hub = new RelayHub(state);
  const socket = makeSocket({ sessionId: "expired", role: "mobile" });

  await hub.webSocketMessage(
    socket,
    JSON.stringify({ type: "command", action: "notepad", request_id: "expired-1" }),
  );

  assert.equal(socket.closed[0]?.code, 4401);
  assert.match(socket.closed[0]?.reason ?? "", /expired or revoked/);
  assert.deepEqual(socket.sent, []);
});

test("a revoked pairing closes an already-authenticated websocket", async () => {
  const hub = new RelayHub(makeState());
  const socket = makeSocket({ sessionId: "revoked", role: "desktop" });

  await hub.webSocketMessage(
    socket,
    JSON.stringify({ type: "result", request_id: "revoked-1", ok: true }),
  );

  assert.equal(socket.closed[0]?.code, 4401);
  assert.deepEqual(socket.sent, []);
});

test("websocket messages are rate-limited per session and role", async () => {
  const sessionId = "limited";
  const state = makeState({
    ["session:" + sessionId]: { sessionId, expiresAt: Date.now() + 60_000 },
  });
  const hub = new RelayHub(state);
  const socket = makeSocket({ sessionId, role: "mobile" });

  for (let index = 0; index < 121; index += 1) {
    await hub.webSocketMessage(
      socket,
      JSON.stringify({ type: "command", action: "notepad", request_id: "req-" + index }),
    );
  }

  assert.equal(socket.sent.length, 121);
  assert.deepEqual(socket.sent.at(-1), { type: "error", error: "rate_limited" });
});

test("oversized websocket messages are rejected before JSON processing", async () => {
  const hub = new RelayHub(makeState());
  const socket = makeSocket(null);

  await hub.webSocketMessage(socket, "x".repeat(4097));

  assert.equal(socket.closed[0]?.code, 1009);
  assert.deepEqual(socket.sent, []);
});
