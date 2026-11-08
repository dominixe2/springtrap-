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


## Local backup and restore

- The local /v1/backup endpoint exports the profile, memories, conversation history, draft-task queue, learning plans and preferences as JSON.
- Backup responses use Cache-Control: no-store; the browser offers a file download rather than placing the backup in browser storage.
- Restore requires an explicit confirmation in the UI, validates every collection and identifier before opening a database transaction, and replaces the included collections atomically. Invalid input or a database error leaves the previous data intact. Tasks interrupted in the running state are re-queued.
- Export and restore share an 8 MiB limit so every generated backup remains restorable by the same version.
- The backup intentionally excludes transient confirmation/session tokens and tool audit records. It also does not include the browser-only offline fallback store.
- A backup contains private notes and conversation history. Store it like a private document and do not add passwords, API keys or other secrets to Micro Helper notes.


## Local Python API boundary

- The local FastAPI service rejects non-loopback Host values on private API routes and applies Origin / Fetch Metadata checks to write requests.
- These checks are CSRF and DNS-rebinding defenses, not authentication. The local Python API does not currently require a user login or bearer token.
- Keep the local service bound to 127.0.0.1. Do not bind it to 0.0.0.0, publish it through a reverse proxy, or expose it directly to a LAN or the public internet.
- This boundary does not protect against another process already running as the same OS user or someone with access to the local account.
