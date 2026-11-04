# Hosted Micro Helper source mirror

This directory tracks the hosted AppDeploy app `micro-helper-ygeuyn`. The live deployment remains on snapshot `1793767519998`; the branch now contains a newer candidate source snapshot `1793769353100`.

- Live app: https://micro-helper-ygeuyn.v2.appdeploy.ai/
- Backend routes and scheduled job: `backend/index.ts` and `cron.json`.
- Main UI: `index.html`; `src/main.ts` initializes the AppDeploy client and realtime connection.
- QA scenarios: `tests/tests.json`.

**Deployment boundary:** AppDeploy runs its own stored source snapshot. This GitHub copy is a reviewable, version-controlled candidate and CI validates it, but a GitHub commit does not automatically publish to AppDeploy. The latest candidate activates the image studio, adds executable AI tasks and selectable response depth. Its AppDeploy publish attempt was blocked by the account usage limit, so the live URL still serves the earlier deployment until credits are available and the candidate is redeployed.

The root project remains a separate local Python/Ollama edition. Do not copy the hosted HTML/backend over the root Python package.

## Source validation

The repository workflow `.github/workflows/hosted-app-checks.yml` checks the mirrored JSON configuration, Czech PWA manifest, API authentication declarations, scheduled review handler, key image/task workflow wiring, QA coverage and inline browser JavaScript syntax. It is a static consistency check, not a live authenticated end-to-end test. Live search, image generation, account sync and browser speech still need verification in a signed-in browser session.
