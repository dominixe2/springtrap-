# Micro Helper

Micro Helper is a free-first, local-first personal assistant foundation. The current branch provides a Czech-first browser UI, optional Ollama chat, persistent local profile, editable private notes, and conversation history stored in SQLite.

## What works in this version

- Local FastAPI service and responsive browser UI.
- Optional local LLM via Ollama. No paid API key is required; a compatible model must be downloaded locally.
- Editable agent name, language, and communication style.
- Local SQLite persistence for profile, user-managed memories, and successful chat messages.
- Memory create/list/edit/delete API and UI controls, plus JSON export of saved notes.\n- Complete portable JSON backup/restore for profile, all saved memories, and full conversation history. Restore requires explicit confirmation and replaces the target device data.
- Conversation history reload and explicit history deletion.
- Ollama model discovery and graceful handling when Ollama is offline.
- API validation and automated tests.

## Android quick start (Termux)

Install [Termux from F-Droid](https://f-droid.org/packages/com.termux/), open it, then run:

```bash
pkg update -y && pkg install -y git
git clone --depth 1 --branch main https://github.com/dominixe2/springtrap-.git
cd springtrap-
bash termux-install.sh
bash termux-start.sh
```

Open `http://127.0.0.1:8000` in Chrome on the same phone. Keep Termux running while using Micro Helper. Android may stop background work unless Termux is excluded from battery optimization.

**Android limitation:** this starts the app, local database, profile, notes, and conversation storage on the phone. The current chat adapter talks to Ollama at `127.0.0.1:11434`; Ollama is not supplied by this Termux installer. Therefore AI replies are not yet available on Android until a compatible on-device inference runtime and adapter are added. No paid API is required.

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

The API binds to localhost by default. Keep it local unless you separately configure authentication and network security. Do not expose this development server directly to the internet.

## Local data and privacy

- Default database: `~/.micro-helper/micro_helper.sqlite3`.
- Override the path with `MICRO_HELPER_DB`.
- Override the Ollama endpoint with `OLLAMA_URL`.
- Stored profile, manually saved memories, and successful chat exchanges stay in that local SQLite database. Deleting conversation history does not delete memory notes.
- Do not store passwords, API keys, or other secrets in memories. The app does not encrypt the SQLite database.

## Honest scope

This is not yet a complete Android or Windows agent package. Voice, wake word, Android system integration, a Windows automation worker, encrypted sync, paired agents, and autonomous tool execution are **not implemented**. It does not control your computer or phone just because chat works. The current local web app is the usable foundation for those future modules.

See `docs/ARCHITECTURE.md` and `docs/PRODUCT_SPEC.md` for the intended architecture and security rules.
