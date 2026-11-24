# Micro Helper

Micro Helper is a Czech-first personal assistant project with a phone-first hosted app and a separate Windows Companion.

## Phone-first hosted app

- **Live app:** https://micro-helper-ygeuyn.v2.appdeploy.ai/
- **Hosted source candidate:** [hosted-app/](hosted-app/)
- **Android:** install the hosted PWA from Chrome, or download the debug APK from [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/android-apk.yml?query=branch%3Amicro-helper).
- **Windows Companion:** download the latest artifact from [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/windows-companion.yml?query=branch%3Amicro-helper).

The GitHub candidate includes account-backed cloud chat and sync, private notes and preferences, learning plans, voice controls, web search, image-studio handlers, and quick/deep response depth. Feature availability depends on the signed-in account and platform AI quotas.

## Deployment status and limits

- The live AppDeploy app remains available at the URL above. Its last confirmed deployed snapshot is `1794022687158`.
- AppDeploy's usage limit blocked the next publication. Newer GitHub branch changes are **not automatically live** in the hosted app.
- The Android APK is a debug-signed WebView wrapper and loads the hosted app. It needs internet for cloud AI and synchronization; it is not a Play Store release.
- The PWA caches its public shell, not AI models or private API responses. There is no offline AI.
- Browser voice and wake phrase support depend on the browser and work only while the app is open.
- The Windows Companion allows only lock, Explorer, Notepad and Calculator. It does not expose arbitrary shell commands or remote desktop.
- The Windows EXE is unsigned; SmartScreen may warn.
- Real-device testing is still required before calling the product release-ready.

## Windows cloud relay

- **Current confirmed staging relay:** https://micro-helper-relay.onrender.com
- **Health:** https://micro-helper-relay.onrender.com/health
- The Render service is confirmed deployed and running. Its in-memory sessions can be lost on restart or free-tier sleep.
- A Cloudflare Worker + Durable Object replacement is now in `cloudflare/`. It is not deployed until the repository secrets are added and the manual GitHub Actions workflow is run.
- See [Cloudflare relay setup](cloudflare/README.md).

## GitHub workflows

- `checks.yml`: local Python package and browser UI checks.
- `hosted-app-checks.yml`: hosted source mirror, JSON, API-route and inline JavaScript checks.
- `android-apk.yml`: installable debug APK artifact with SHA-256 checksum.
- `windows-companion.yml`: standalone Windows Companion EXE.
- `cloudflare-deploy.yml`: manual Cloudflare Worker + Durable Object deployment after secrets are configured.

## Local Python edition

The root `src/micro_helper` package is a separate local FastAPI application. It can use a model running through Ollama. It is not the backend serving the hosted URL.

Requires Python 3.11+:

```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn micro_helper.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and run `pytest -q` for local tests.

### Encrypted offline workspace (local Python edition)

After the local API is available and you create an encrypted backup (or import one), the browser can reopen that copy without the API:

- The vault uses AES-256-GCM with PBKDF2-SHA-256 and stores only the encrypted envelope in IndexedDB. The passphrase is not stored.
- When the local API cannot verify a session, the normal chat and server-backed data stay locked. Only the separately scoped encrypted-vault panel remains interactive.
- After entering the vault passphrase, you can view and edit memories and preferences, review the saved conversation history, and inspect saved tasks and learning plans. Clearing the offline history and deleting a memory or preference require explicit confirmation.
- Every offline edit is re-encrypted before it is persisted. It changes only this browser's offline copy; there is no automatic merge or sync with the local SQLite database. Restoring that copy to the app requires the API to be online, an authenticated session and a separate confirmation.
- The vault UI clears decrypted content on manual lock, inactivity timeout, page backgrounding and page unload. The service worker precaches the vault code but still never caches private `/v1/` API responses. Offline AI/chat is not provided.

Real-browser IndexedDB timing and physical Android/Windows acceptance are still required; the automated Node controller tests do not replace those checks.
