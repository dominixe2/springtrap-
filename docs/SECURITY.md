# Micro Helper security notes

## Hosted account data

- User-facing API routes in the hosted backend require an authenticated AppDeploy user.
- State is stored in per-user tables derived from the authenticated user ID; route handlers use the authenticated identity rather than accepting a caller-supplied owner ID.
- Realtime subscriptions are checked against the authenticated user's own `user_state` entity.
- The service worker caches only the public app shell and static assets. It deliberately skips API paths and does not cache private API responses.
- Do not put passwords, API keys or other secrets into notes or preferences.

## Web and image tools

- Web search builds a fixed DuckDuckGo HTML search URL from the query. It does not accept an arbitrary URL from the browser, reducing SSRF exposure.
- Extracted result links are restricted to HTTP(S), deduplicated and rendered as links with `noopener noreferrer`.
- Image upload routes require authentication, accept JPEG/PNG/WebP, cap each image at 6 MiB and cap generation to five references.
- AI failures are returned as visible service errors rather than fabricated successful results.

## Windows Companion

- Binds only to `127.0.0.1:8765`.
- Accepts browser POST requests only from the exact hosted app origin.
- Uses a random one-time pairing code and a random session bearer token; restarting the process invalidates both.
- Limits pairing attempts and accepts only a fixed allowlist: lock Windows, Explorer, Notepad and Calculator.
- Does not invoke a shell or accept arbitrary executable paths/arguments.
- The local bridge is not a general remote desktop. Keep the executable from a trusted build artifact and close it when it is not needed.

## Residual risks and limits

- The Android wrapper loads the hosted origin, so cloud data and AI depend on network and the AppDeploy account.
- The current APK is debug-signed. Do not publish it as a Play Store release. A production signing key and a protected release-signing workflow are still required for store distribution.
- The Windows EXE is not code-signed; Windows SmartScreen may display a warning.
- The browser-local fallback uses browser storage and is not encrypted by this app. Treat device access and browser profile security accordingly.
- A successful CI build proves packaging and static checks, not behavior on the user's physical phone or notebook.


## Local API tool policy integration (2026-11-07)

- The local Python API now evaluates registered tool calls through `src/micro_helper/trust_policy.py`.
- Only the exact low-risk reads `profile.read` and `memory.list` have built-in grants. Unknown tool IDs remain unavailable.
- `memory.create` is classified as a state-changing local write and requires a one-time confirmation token bound to the normalized arguments. Tokens expire after 60 seconds, are stored only as SHA-256 hashes, and are consumed atomically once.
- The `/v1/audit` endpoint records tool ID, capability, operation, policy decision, reason and outcome. It deliberately does not store tool arguments, results, or confirmation tokens.
- This integration covers only the three registered local API tools. It does not yet protect every hosted, Windows Companion, or JARVIS adapter. There is no user-managed grant editor/revocation UI yet; do not imply otherwise.
- The confirmation endpoint must only be called after the client has displayed the exact action and received explicit user approval. The token is a short-lived server-side replay guard, not authentication. The local API must remain bound to loopback; Origin/Fetch-Metadata checks are defense in depth, not a substitute for authentication.


## Shared REST mutation authorization (2026-11-09)

- Every state-changing local REST route present in the trust-gateway branch is classified by one shared route resolver and evaluated by the deterministic trust policy.
- Profile, memory, preference, learning-plan, task-queue and conversation-clear writes require a short-lived, single-use confirmation token bound to the exact HTTP method, path and canonical JSON body. The token is stored only as a SHA-256 hash and is consumed atomically.
- Chat submission has one narrow built-in grant because the user explicitly presses Send; it does not authorize any other conversation or memory mutation.
- The browser UI displays the exact method, path and request body before requesting a token. The offline localStorage fallback uses an in-memory, one-time token with the same method/path/body binding; reloading the page invalidates outstanding offline confirmations.
- Audit events store action metadata only, never private request bodies or confirmation tokens.
- These tokens are an explicit-action/replay guard, **not authentication**. The local API must remain loopback-only. This branch is stacked on PR #23; the separate PR #25 backup-restore endpoint must be brought through this same gate when the two branches are integrated.


## Full local backup/restore policy gate (2026-11-09)

- Full backup export uses `Cache-Control: no-store` and is capped at the same 8 MiB format limit accepted by restore.
- Exported backups are plaintext JSON, not encrypted by the app, and contain the complete local profile, memories, conversation history, tasks, learning plans and preferences. The UI must warn before download; users should store the file privately and never send it as a public attachment.
- The separate memory-notes export is also plaintext JSON and contains private notes; the UI must warn before downloading it as well.
- Restore is classified as a destructive `backup.restore` action and passes through the shared Adaptive Trust Engine route gate before database replacement.
- The browser displays a restore-specific summary (collection counts and byte size). It hashes the exact request bytes with Web Crypto; only the SHA-256 digest is sent to the confirmation endpoint, so the private backup body is not copied into confirmation storage or audit events.
- The resulting token is short-lived, single-use and bound to the exact restore body bytes. The ASGI body-limit middleware enforces 8 MiB on both declared and chunked requests before JSON parsing.
- All `/v1` local API responses, including private reads and rejected requests, use `Cache-Control: no-store` and `Pragma: no-cache` to reduce retention of profile, memory, history and backup data by browsers or intermediaries.
- The local API remains loopback-only. Middleware checks both the Host/Origin hostname and the actual ASGI socket peer IP; a caller cannot bypass the boundary by sending `Host: localhost` from a LAN address. The confirmation token is an action/replay guard, not authentication.

## Local single-user API authentication

- The first run requires an exact same-origin setup request and a password of at least 12 characters.
- Passwords are stored only as salted scrypt hashes in the local SQLite database; plaintext passwords are not persisted.
- Successful setup/login issues an opaque 12-hour HttpOnly, SameSite=Strict session cookie. Only the SHA-256 hash of the cookie value is stored in SQLite; the raw value is never returned in JSON or written to browser storage.
- All private /v1 routes require a valid unexpired local session, except the minimal status/setup/login/logout endpoints.
- All state-changing /v1 requests require an exact Origin; setup, login and logout always require the exact same origin.
- Failed login attempts are rate-limited to five per 15 minutes per local process. This in-memory limiter resets when the process restarts.
- Logout revokes the server-side session immediately. The cookie expires after 12 hours.
- This is single-user authentication for a loopback-only local instance, not multi-user cloud authentication or a way to expose the API to a LAN.
- Password recovery is not implemented yet. Keep a separate backup before any manual recovery procedure.
- The browser UI does not put the password or session value into localStorage or sessionStorage.
