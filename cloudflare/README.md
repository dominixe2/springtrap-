# Cloudflare relay deployment

This folder contains the durable replacement for the Render staging relay.

## What it deploys

- Cloudflare Worker: `micro-helper-relay`
- Durable Object class: `RelayHub`
- Persistent session metadata and pairing records in Durable Object SQLite storage
- HTTP API compatible with the current pairing flow:
  - `POST /v1/pair/register`
  - `POST /v1/pair/claim`
  - `POST /v1/pair/revoke`
  - `GET /health`
  - `wss://<worker-host>/v1/ws`

The worker allows only the four fixed Windows actions: `lock`, `explorer`, `notepad`, and `calculator`. Pairing registration and claims are rate-limited. Registration and one-time claim are performed inside Durable Object storage transactions to prevent simultaneous duplicate claims.

## Connect Cloudflare to this repository

1. In Cloudflare, create an API token using the **Edit Cloudflare Workers** template. Restrict it to the one account that will host this Worker. Do not paste the token into ChatGPT or commit it to the repository.
2. Copy the Cloudflare **Account ID** from the account overview.
3. In this GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
4. Add these two repository secrets:
   - `CLOUDFLARE_API_TOKEN`: the scoped API token
   - `CLOUDFLARE_ACCOUNT_ID`: the account ID
5. Open **Actions → Deploy Micro Helper Cloudflare Relay → Run workflow** and start the workflow on branch `micro-helper`.

The deploy workflow is manual by design. A push cannot accidentally attempt a deployment before the secrets have been configured.

## Validation and endpoint

- `Cloudflare Relay Checks` validates JavaScript syntax and Wrangler configuration on pushes and pull requests.
- `Deploy Micro Helper Cloudflare Relay` performs the authenticated deployment only when manually started.
- The workflow log prints the deployed `workers.dev` hostname. Confirm `GET https://<worker-host>/health` returns `status: ok` before changing any clients.
- After a successful deploy, the Windows Companion and hosted app still need their relay base URLs switched from Render to the confirmed Cloudflare hostname. Do not switch clients before the health check succeeds.

## Cost and release caveats

Cloudflare's plan limits and Durable Objects billing can change. Check the current account pricing and usage before enabling production traffic; do not assume that sustained usage is guaranteed to cost 0 Kč. This implementation has not yet been deployed or tested against a live Cloudflare account.

## Security

- Never put API tokens in source files, chat messages, screenshots, or workflow logs.
- The Worker accepts browser API requests only from the official Micro Helper origin.
- Pairing tokens are hashed before storage; the mobile token is returned only once at claim time.
- Pairing codes expire after five minutes and can be claimed only once.
- Revocation deletes the pairing and closes active sockets.
- No arbitrary shell commands are accepted or forwarded.
