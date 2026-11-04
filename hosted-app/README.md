# Hosted Micro Helper source mirror

This directory tracks the hosted AppDeploy app `micro-helper-ygeuyn`. The live deployment remains on snapshot `1793767519998`; the branch now contains a newer candidate source snapshot `1793769353100`.

- Live app: https://micro-helper-ygeuyn.v2.appdeploy.ai/
- Backend routes and scheduled job: `backend/index.ts` and `cron.json`.
- Main UI: `index.html`; `src/main.ts` initializes the AppDeploy client and realtime connection.
- QA scenarios: `tests/tests.json`.

**Deployment boundary:** AppDeploy runs its own stored source snapshot. This GitHub copy is a reviewable, version-controlled mirror and CI validates it, but a GitHub commit does not automatically publish to AppDeploy. When changing hosted behavior, update this mirror and the AppDeploy snapshot together, then verify the live deployment.

The root project remains a separate local Python/Ollama edition. Do not copy the hosted HTML/backend over the root Python package.

## Source validation

The repository workflow `.github/workflows/hosted-app-checks.yml` checks the mirrored JSON configuration, Czech PWA manifest, API authentication declarations, scheduled review handler, and inline browser JavaScript syntax. It is a static consistency check, not a live authenticated end-to-end test. Live search, image generation, account sync and browser speech still need verification in a signed-in browser session. The candidate's inline scripts are syntax-checked by CI before a future deployment.
