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
- An explicit backend tool registry: profile read, memory list, and confirmation-gated local memory creation. Arbitrary shell commands and code execution are not exposed.
- Basic Czech browser voice input (SpeechRecognition where supported) and spoken replies (browser speech synthesis), with a stop control. This is a first voice layer, not a live duplex conversation.
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
- **Live duplex voice with barge-in, wake word, and background listening are not implemented.** Basic browser voice depends on browser speech APIs, microphone permission, and network/browser support; it is not guaranteed offline.
- Native Android integration, Windows automation worker, encrypted sync, paired devices, model-driven tool selection, and broad autonomous tool execution are not implemented. The current three-tool registry is a constrained foundation, not general device control.

## Local data and privacy

- Default backend database: `~/.micro-helper/micro_helper.sqlite3`.
- Override the path with `MICRO_HELPER_DB`; override Ollama with `OLLAMA_URL`.
- Browser fallback data is stored in that browser's localStorage and can be cleared by browser data cleanup. The app does not currently encrypt either store.
- Do not store passwords, API keys, or other secrets in memories.

See `docs/ARCHITECTURE.md`, `docs/PRODUCT_SPEC.md`, and `docs/MOBILE_AND_SYNC_PLAN.md` for architecture and future sync requirements.


## Background task worker (experimental)

The branch now includes a persistent SQLite task queue for bounded `agent.draft` jobs. Start the API, then start a separate worker process against the same database:

```powershell
# Terminal 1
uvicorn micro_helper.api:app --host 127.0.0.1 --port 8000

# Terminal 2
micro-helper-worker
```

The worker polls the queue and uses the configured Ollama endpoint (`OLLAMA_URL`, default `http://127.0.0.1:11434`) with the `llama3.2` model. It can also process one queued job and exit with `micro-helper-worker --once`. Tasks can be created and inspected through `POST /v1/tasks`, `GET /v1/tasks`, and `GET /v1/tasks/{id}`; queued or running work can be cancelled.

This is an initial job runner, not yet an autonomous general-purpose agent. It only creates text drafts; it cannot run shell commands, browse the web, control devices, send messages, or perform external side effects. If Ollama is unavailable, the task is marked failed rather than pretending it completed.

**Cloud warning:** the Google Cloud Always Free `e2-micro` VM has 1 GB RAM and is suitable only for a lightweight API/queue, not for hosting a useful local LLM. The current API also has no remote-user authentication, so do not expose it to the public internet or deploy it as a phone-accessible cloud service yet. A secure pairing/authentication layer and a genuinely free model-provider strategy are still required before cloud deployment.
