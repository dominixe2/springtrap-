# Hosted Micro Helper source mirror

This directory tracks the hosted AppDeploy app `micro-helper-ygeuyn`. The active deployment snapshot is `1793769353100`; the GitHub branch contains the corrected candidate source.

- Live app: https://micro-helper-ygeuyn.v2.appdeploy.ai/
- Backend routes and scheduled job: `backend/index.ts` and `cron.json`.
- Main UI: `index.html`; `src/main.ts` initializes the AppDeploy client and realtime connection.
- QA scenarios: `tests/tests.json`.

**Deployment status:** The active AppDeploy snapshot currently reports a frontend JavaScript syntax error in the task-list script. The corrected GitHub candidate fixes that error, activates the image-studio controls, adds executable AI tasks and selectable response depth. Publishing the correction is blocked by the AppDeploy account usage limit. Do not treat the corrected candidate as live until a redeployment reaches `ready` with no frontend errors.

GitHub commits do not automatically publish to AppDeploy. Keep this candidate and the deployed snapshot aligned after the deployment limit is resolved.

The root project remains a separate local Python/Ollama edition. Do not copy the hosted HTML/backend over the root Python package.

## Source validation

The repository workflow `.github/workflows/hosted-app-checks.yml` checks the mirrored JSON configuration, Czech PWA manifest, API authentication declarations, scheduled review handler, key image/task workflow wiring, QA coverage and inline browser JavaScript syntax. It is a static consistency check, not a live authenticated end-to-end test. Live search, image generation, account sync and browser speech still need verification in a signed-in browser session.
