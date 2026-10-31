# Micro Helper: phone + notebook plan

## Product direction

Micro Helper should be one product on Android and Windows, with the same profile, notes, settings, and conversation history. Installing the app on two devices is not the same as sharing an account: shared data requires a deliberate sync mechanism.

## Work prepared in this branch

- Responsive browser UI remains the shared interface.
- A web app manifest and app icon describe the installable app.
- A service worker caches only the static app shell for offline opening.
- API endpoints and private data are explicitly excluded from service-worker caching.

## Current limitations

- This does not yet create a native APK or Microsoft Store package.
- Offline shell availability does not make AI chat work offline. The API and a local Ollama model must be running and reachable.
- There is no sign-in/account system or cross-device sync endpoint yet.
- The current SQLite database remains local to the computer running the API.
- Browser installation generally requires HTTPS, except for localhost. A phone cannot access the notebook's localhost address as if it were the same device.

## Recommended zero-cost sync architecture

1. Keep the same web UI for Android and Windows; later package it for Android if needed.
2. Add explicit device pairing with a one-time code and a long random device secret. Never expose the unauthenticated development API to the public internet.
3. For initial setup, support same-Wi-Fi pairing with clear consent, authentication, and a narrow sync-only API. Do not bind the existing API to all network interfaces before authentication and firewall rules exist.
4. Use stable IDs and per-record updated timestamps for profile, notes, and messages. Keep tombstones for deletions so deleted notes do not reappear.
5. Detect concurrent edits and ask the user which version to keep instead of silently overwriting.
6. Encrypt transport, keep secrets out of logs, and provide export/restore before first sync.
7. For sync away from home, use an optional self-hosted endpoint or an explicitly chosen secure relay. A free public relay is not assumed or promised.

## Acceptance checks

- The app shell opens after a first successful online load while offline.
- API requests are not served from cache.
- Phone and notebook use the same product UI.
- Pairing is authenticated before any sync data can be read or changed.
- Notes and profile changes sync in both directions, including deletion and conflict handling.
- Export/restore remains available if sync fails.
