# Hosted Micro Helper source mirror

This directory mirrors the hosted AppDeploy snapshot `micro-helper-ygeuyn` (snapshot `1793767519998`, 2026-11-04).

- Live app: https://micro-helper-ygeuyn.v2.appdeploy.ai/
- Backend routes and scheduled job: `backend/index.ts` and `cron.json`.
- Main UI: `index.html`; `src/main.ts` initializes the AppDeploy client and realtime connection.
- QA scenarios: `tests/tests.json`.

**Deployment boundary:** AppDeploy runs its own stored source snapshot. This GitHub copy is a reviewable, version-controlled mirror and CI validates it, but a GitHub commit does not automatically publish to AppDeploy. When changing hosted behavior, update this mirror and the AppDeploy snapshot together, then verify the live deployment.

The root project remains a separate local Python/Ollama edition. Do not copy the hosted HTML/backend over the root Python package.
