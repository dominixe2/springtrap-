# Micro Helper

Micro Helper is a free-first, local-first personal assistant foundation. The current branch provides a Czech-first responsive web UI, optional local Ollama chat, persistent local profile and notes, conversation history, and an installable progressive web app shell.

## What works in this branch

- Responsive browser UI intended to be shared between phone and notebook.
- PWA manifest, app icon, and service worker for caching the static app shell after a successful online visit.
- Browser-local fallback for profile, notes, and conversation history when the API cannot be reached. This fallback uses localStorage on that device and is not automatically synchronized with the server or another device.
- FastAPI backend with SQLite persistence for profile, user-managed memories, and successful AI chat exchanges.
- Optional local LLM via Ollama. No paid API key is required; a compatible model must be downloaded locally.
- Memory create/list/edit/delete controls and JSON export of saved notes.
- Conversation history reload and explicit history deletion.
- API validation and automated tests.

## Windows quick start

Requires Python 3.11+ and, for AI chat, [Ollama](https://ollama.com/) with a model installed.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
# Optional local AI: install Ollama separately, then run e.g. ollama pull llama3.2
uvicorn micro_helper.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. In another terminal, run `pytest -q` to validate the backend.

For PWA installation, deploy behind HTTPS or open the app on localhost, visit it online once, then use the browser's Install app / Add to Home Screen option when offered. A service worker cannot be installed from an ordinary insecure remote HTTP site.

The API binds to localhost by default. Keep it local unless you separately configure authentication and network security. Do not expose this development server directly to the internet.

## Offline and cross-device limits

- The service worker caches the app shell, not private API responses.
- If the API is unreachable, profile, notes, and a basic conversation log can use browser-local storage on that device. Browser-local fallback data is separate from the server's SQLite database.
- **Offline AI generation is not implemented.** The app needs a model running locally and reachable by the API. A cached web page alone is not an AI model.
- **Cross-device sign-in and synchronization are not implemented yet.** The browser-local fallback does not sync to a notebook or phone.
- A native Android APK and Microsoft Store package are not produced by this branch yet.
- Voice, wake word, Android system integration, Windows automation worker, encrypted sync, paired devices, and autonomous tool execution are not implemented.

## Local data and privacy

- Default backend database: `~/.micro-helper/micro_helper.sqlite3`.
- Override the path with `MICRO_HELPER_DB`; override Ollama with `OLLAMA_URL`.
- Browser fallback data is stored in that browser's localStorage and can be cleared by browser data cleanup. The app does not currently encrypt either store.
- Do not store passwords, API keys, or other secrets in memories.

See `docs/ARCHITECTURE.md`, `docs/PRODUCT_SPEC.md`, and `docs/MOBILE_AND_SYNC_PLAN.md` for architecture and future sync requirements.
