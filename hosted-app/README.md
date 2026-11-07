# Hosted Micro Helper source mirror

This directory tracks the hosted AppDeploy app `micro-helper-ygeuyn`.

- Live app: https://micro-helper-ygeuyn.v2.appdeploy.ai/
- Latest verified live snapshot: `1794022687158` (2026-11-07).
- Live status at last verification: `ready`; frontend and backend error lists empty.
- Backend routes and scheduled job: `backend/index.ts` and `cron.json`.
- Main UI: `index.html`; `src/main.ts` initializes the AppDeploy client and authenticated realtime connection.
- QA scenarios: `tests/tests.json` (five focused scenarios).

## Deployment boundary

The live app remains on the verified snapshot above. The GitHub branch `micro-helper` now contains a newer source candidate with:
- automatic WebSocket reconnection after network interruption and mobile app resume;
- corrected realtime delivery payloads;
- refreshed saved conversation context after cross-device updates;
- PWA v3 asset caching that excludes API and private account data;
- updated regression coverage.

The candidate is committed and the hosted-source validation workflow passed. GitHub commits do **not** automatically publish to AppDeploy. A new AppDeploy deployment attempt was blocked by the AppDeploy account usage limit, so none of the newer candidate changes should be described as live until a deployment reaches `ready`.

The last successful Android APK artifact was built from an earlier commit. Rebuild it after the AppDeploy deployment is available again so the APK points to the intended current hosted release.

The root project remains a separate local Python/Ollama edition. Do not copy the hosted HTML/backend over the root Python package.

## Source validation

The repository workflow `.github/workflows/hosted-app-checks.yml` checks the mirrored JSON configuration, Czech PWA manifest, API authentication declarations, scheduled review handler, key image/task workflow wiring, QA coverage and inline browser JavaScript syntax. It is a static consistency check, not a live authenticated end-to-end test. Live search, image generation, account sync, browser speech and Windows pairing still need verification in real signed-in device sessions.
