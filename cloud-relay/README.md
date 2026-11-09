# Micro Helper Cloud Relay

The relay connects the Windows Companion to the signed-in Micro Helper web app without exposing a listening port on the user's PC.

## Current client endpoint: Render staging relay

- HTTP: https://micro-helper-relay.onrender.com
- WebSocket: wss://micro-helper-relay.onrender.com/v1/ws
- Health: https://micro-helper-relay.onrender.com/health

The Windows Companion source currently points to this Render endpoint. The Cloudflare Worker below is a separate replacement and is not the active Windows Companion endpoint.

The Render implementation keeps the session registry and live sockets in process memory. Pairings are lost on process restart or free-tier sleep. This PR changes source and tests only; it does not deploy to Render or verify the live service.

## Cloudflare durable replacement

A Worker + Durable Object implementation is available in [../cloudflare/](../cloudflare/). It persists pairing/session metadata in Durable Object storage. It is a separate implementation and has not been deployed or production-tested.

Before switching clients, deploy and verify the Worker, then update both the Windows Companion and hosted app endpoint together. Do not assume the Cloudflare Worker protects the current Render connection.

## Pairing flow

1. Windows Companion generates a random desktop token and a six-digit one-time pairing code.
2. It registers the code and the SHA-256 hash of its desktop token with `POST /v1/pair/register`.
3. The user enters the code in the Micro Helper Windows panel.
4. The browser claims it with `POST /v1/pair/claim`, receiving a separate mobile token.
5. Each side opens `/v1/ws` and sends its token in the first WebSocket frame, not in the URL.
6. The browser can revoke the whole pairing with `POST /v1/pair/revoke`; both tokens and both sockets are invalidated.

## Security boundaries

- Pairing codes expire after five minutes and can be claimed once; claimed sessions expire after twelve hours.
- Registration is limited to 20 attempts per client IP per five minutes; claims are limited to 8 per client IP per five minutes. The in-memory limiter map is bounded.
- The browser HTTP API uses CORS for the exact hosted app origin. Mobile WebSockets must present that exact Origin. The non-browser Windows Companion may omit Origin but must authenticate with its desktop token.
- The relay rechecks the token-to-session mapping before processing every WebSocket message, so an expired or revoked socket cannot continue issuing commands.
- At most 20 device commands may be pending; stale pending entries expire after two minutes. Duplicate request IDs and results without a matching pending command are rejected.
- A paired mobile session may send at most 30 commands per minute.
- Only four fixed actions are forwarded: `lock`, `explorer`, `notepad`, `calculator`.
- Desktop execution uses a fixed executable allowlist and `shell=False`; arbitrary shell/PowerShell commands are never forwarded.
- Tokens are stored as SHA-256 hashes by the relay. Session state remains ephemeral and is not a durable device registry.

## Local tests

```powershell
python -m pip install -r requirements.txt
python -m pytest -q tests
```
