# Micro Helper Cloud Relay

The relay connects the Windows Companion to the signed-in Micro Helper web app without exposing a listening port on the user's PC.

## Current staging endpoint

- HTTP: https://micro-helper-relay.onrender.com
- WebSocket: wss://micro-helper-relay.onrender.com/v1/ws
- Hosting: Render Free, Frankfurt
- Health: `GET /health`

## Pairing flow

1. Windows Companion generates a random desktop token and a six-digit one-time pairing code.
2. It registers the code and the SHA-256 hash of its desktop token with `POST /v1/pair/register`.
3. The user enters the code in the Micro Helper Windows panel.
4. The browser claims it with `POST /v1/pair/claim`, receiving a separate mobile token.
5. Each side opens `/v1/ws` and sends its token in the first WebSocket frame, not in the URL.
6. The browser can revoke the whole pairing with `POST /v1/pair/revoke`; both tokens and both sockets are invalidated.
6. The relay forwards only four fixed actions: `lock`, `explorer`, `notepad`, `calculator`. It returns bounded result messages.

## Security boundaries

- Tokens are stored as SHA-256 hashes in relay memory.
- Pairing codes expire after five minutes and can be claimed once.
- Pairing claims are rate-limited per client IP.
- Desktop registration is rate-limited per client IP.
- Browser WebSocket connections must originate from the official Micro Helper app origin.
- Messages are schema-checked and bounded; arbitrary shell/PowerShell commands are never forwarded.
- Desktop execution uses a fixed executable allowlist and `shell=False`.

## Staging limitations

This is a staging relay, not yet a durable always-on production service:
- Session registry and live sockets are in process memory. A service restart loses pairings and requires a fresh pairing code.
- Render Free services can spin down after inactivity and take time to wake. A reconnect may require the user to pair again if the process restarted.
- Do not use this staging relay as the only path for unattended critical PC operations.
- The app's AppDeploy-hosted UI still needs a new AppDeploy release before the cloud-pairing panel is available to users. GitHub source validation does not publish to AppDeploy.

## Local tests

From this directory:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q tests
```
