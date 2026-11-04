# Micro Helper

Micro Helper is a Czech-first personal assistant project with two deliberately separate editions.

## Phone-first hosted app

- **Live app:** https://micro-helper-ygeuyn.v2.appdeploy.ai/
- **Hosted source mirror:** [hosted-app/](hosted-app/)
- **Install on Android:** use the hosted PWA from Chrome, or download the debug APK from [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/android-apk.yml?query=branch%3Amicro-helper).
- **Windows Companion:** build/download it from [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/windows-companion.yml?query=branch%3Amicro-helper).

The hosted edition includes account-backed cloud chat and sync, private notes and preferences, learning plans, draft tasks, daily review reports, browser voice, web search, image generation, image analysis and OCR. Feature availability depends on the signed-in account and platform AI quotas.

### Honest platform limits

- The Android APK is currently a debug-signed WebView wrapper. It loads the hosted app and needs internet for cloud AI and synchronization. It is not a Play Store release.
- The PWA caches its public shell, not AI models or private API responses. There is no offline AI.
- Browser voice and wake phrase support depend on the browser and work only while the app is open and voice mode is active.
- Background tasks create bounded text drafts; they are not a general autonomous agent.
- The Windows Companion permits only lock, Explorer, Notepad and Calculator. It does not expose arbitrary shell commands or remote desktop.
- The Windows EXE is not code-signed; SmartScreen may warn.
- The GitHub `hosted-app/` directory is a version-controlled mirror of the AppDeploy source snapshot. GitHub commits do not automatically publish to AppDeploy, so update both when changing the hosted product.

See [hosted app architecture](docs/HOSTED_APP.md) and [security notes](docs/SECURITY.md).

## Local Python edition

The root `src/micro_helper` package is a separate local FastAPI application. It can use a model running through Ollama and is useful for local development. It is not the backend serving the hosted URL.

### Windows quick start

Requires Python 3.11+.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
# Optional local AI: install Ollama, then e.g. ollama pull llama3.2
uvicorn micro_helper.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Run `pytest -q` to execute the local Python tests.

## GitHub checks

- `checks.yml`: local Python package and browser UI checks.
- `hosted-app-checks.yml`: hosted source mirror, JSON, authenticated API-route and inline JavaScript checks.
- `android-apk.yml`: installable debug APK artifact with a SHA-256 checksum.
- `windows-companion.yml`: standalone Windows Companion EXE.
