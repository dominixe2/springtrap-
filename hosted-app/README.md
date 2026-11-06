# Hosted Micro Helper source mirror

This directory tracks the hosted AppDeploy app `micro-helper-ygeuyn`.

- Live app: https://micro-helper-ygeuyn.v2.appdeploy.ai/
- Backend routes and scheduled job: `backend/index.ts` and `cron.json`.
- Main UI: `index.html`; `src/main.ts` initializes the AppDeploy client and realtime connection.
- QA scenarios: `tests/tests.json`.

## Deployment verification (2026-11-06)

The AppDeploy status endpoint reports the existing deployment as `ready`, with valid configuration. Its latest QA snapshot reports zero frontend and network errors, and a live read-only fetch returned HTTP 200 with the Czech app interface.

Historical runtime logs still contain earlier `Unexpected token ';'` errors at the task-list script. They are retained as historical evidence; the latest QA snapshot does not report those errors as current. This check does not prove that signed-in workflows such as AI chat, task execution, image generation, web search, voice or cross-device synchronization work end to end.

The GitHub source mirror and the deployed AppDeploy snapshot are separate. A passing source check or a GitHub commit does not publish the hosted app. Verify the exact deployed snapshot and signed-in workflows before calling it a production release.

The root project remains a separate local Python/Ollama edition. Do not copy the hosted HTML/backend over the root Python package.

## Source validation

The repository workflow `.github/workflows/hosted-app-checks.yml` checks the mirrored JSON configuration, Czech PWA manifest, API authentication declarations, scheduled review handler, key image/task workflow wiring, QA coverage and inline browser JavaScript syntax. It is a static consistency check, not a live authenticated end-to-end test. Live search, image generation, account sync and browser speech still need verification in a signed-in browser session.
