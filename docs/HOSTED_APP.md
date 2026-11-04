# Hosted Micro Helper

## Architecture

The phone-first hosted app is deployed at https://micro-helper-ygeuyn.v2.appdeploy.ai/. Its reviewable source mirror lives in `hosted-app/`. AppDeploy supplies the authenticated client, backend SDK, AI services, database and realtime transport.

The repository also retains a separate local Python/FastAPI edition in `src/micro_helper`. That edition is useful for local development with Ollama. It is not the backend used by the hosted URL.

## Current capabilities

- Czech-first responsive interface and PWA install support.
- Account-backed cloud chat and private per-user state.
- Notes, preferences, learning plans, conversation history, draft tasks and daily review reports.
- Browser voice input/output, optional hands-free continuation and a foreground-only wake phrase where supported by the browser.
- Authenticated web search, AI image generation, image analysis and OCR.
- Realtime notifications between clients signed into the same account.
- Optional Windows Companion with loopback-only pairing and a small fixed command allowlist.
- Android debug APK wrapper that opens the hosted app.

## Important limits

- The Android APK is a debug-signed WebView wrapper, not a Play Store release. It requires internet for hosted AI and cloud sync.
- The PWA caches the app shell only. It does not cache AI models, private API responses or provide offline AI.
- Browser speech recognition depends on browser/OS support and may use an online speech service. Wake phrase recognition only runs while the app is open and voice mode is active.
- Web search and AI image features depend on AppDeploy AI service availability and account quotas.
- Background tasks currently store bounded draft requests. They are not a general autonomous agent and do not run arbitrary code or operate devices.
- Realtime events notify clients to reload account state; they do not broadcast private state payloads.
- Local browser fallback data remains specific to that browser/device until explicitly imported into the signed-in account.
- The Windows Companion is intentionally limited to lock, Explorer, Notepad and Calculator. It does not expose a shell, arbitrary file access or remote desktop.

## Build and validation

- Android wrapper: `android-wrapper/`, workflow `.github/workflows/android-apk.yml`.
- Windows Companion: `windows-companion/`, workflow `.github/workflows/windows-companion.yml`.
- Hosted mirror validation: `scripts/verify_hosted_app.py`, workflow `.github/workflows/hosted-app-checks.yml`.
- The GitHub mirror is not automatically deployed to AppDeploy. Keep the mirror and deployed snapshot aligned when making changes.
