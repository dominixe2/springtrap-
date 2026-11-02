# Micro Helper testing

## Automatic browser checks (free)

Every push and pull request runs GitHub Actions:
- existing FastAPI/API tests;
- Chromium browser smoke tests at Android-sized viewports;
- responsive overflow and core UI checks;
- PWA manifest and root service-worker checks;
- chat interaction using a mocked model response (no paid API or Ollama required).

Open the repository's **Actions** tab to see each run, logs, and pass/fail status. The tests use a temporary SQLite database and do not touch personal data.

## Test on a real Android phone

Playwright's mobile viewport is browser emulation, not a physical Android device. For a real-device check, open the deployed PWA in Chrome on Android and use Chrome's menu **Install app** / **Add to Home screen**. Confirm launch, rotation, keyboard behavior, offline app-shell launch, and API availability.

Firebase Test Lab is intentionally not wired into CI yet: it requires a Google Cloud project and device-test configuration, and this repository currently ships a web/PWA app rather than a native APK. Do not add cloud credentials or API keys just to run the free browser suite.

## Local run

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m pytest -q
```
