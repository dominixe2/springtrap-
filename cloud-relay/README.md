# Micro Helper Cloud Relay

The relay connects the Windows Companion to the signed-in Micro Helper web app without exposing a listening port on the user's PC.

## Current staging relay: Render

- HTTP: https://micro-helper-relay.onrender.com
- WebSocket: wss://micro-helper-relay.onrender.com/v1/ws
- Health: https://micro-helper-relay.onrender.com/health
- Hosting: Render Free, Frankfurt
- The latest inspected Render deployment is confirmed `live`.

The Render implementation keeps session registry and live sockets in process memory. A restart or free-tier sleep can invalidate pairings.

## Cloudflare durable replacement

A Worker + Durable Object implementation is available in [../cloudflare/](../cloudflare/). It persists pairing/session metadata in Durable Object storage and supports the same HTTP and WebSocket paths. It has **not** been deployed or production-tested yet.

Follow [Cloudflare setup](../cloudflare/README.md). After deploying, update the relay base URL in the Windows Companion and hosted app before switching clients to the Cloudflare endpoint.

## Pairing flow

1. Windows Companion generates a random desktop token and a six-digit one-time pairing code.
2. It registers the code and the SHA-256 hash of its desktop token with `POST /v1/pair/register`.
3. The user enters the code in the Micro Helper Windows panel.
4. The browser claims it with `POST /v1/pair/claim`, receiving a separate mobile token.
5. Each side opens `/v1/ws` and sends its token in the first WebSocket frame, not in the URL.
6. The browser can revoke the whole pairing with `POST /v1/pair/revoke`; both tokens and both sockets are invalidated.

## Security boundaries

- Tokens are stored as SHA-256 hashes by the relay.
- Pairing codes expire after five minutes and can be claimed once.
- Pairing registration and claims are rate-limited per client IP.
- Browser requests and WebSocket connections are restricted to the official Micro Helper origin.
- Only four fixed actions are forwarded: `lock`, `explorer`, `notepad`, `calculator`.
- Desktop execution uses a fixed executable allowlist and `shell=False`; arbitrary shell/PowerShell commands are never forwarded.

## Local tests

```powershell
python -m pip install -r requirements.txt
python -m pytest -q tests
```
