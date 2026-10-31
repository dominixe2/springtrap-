# Micro Helper

Free-first, local-first personal AI agent for Android and Windows. The agent's identity, memory, permissions and tools are the product. An animated mascot is optional decoration only.

## Free setup
- The local core needs no paid API key or subscription.
- Python backend and local browser UI run on your own computer.
- Optional local language model through Ollama; inference uses your own hardware.
- Voice, Android system integrations, cloud sync and remote access are separate modules and may have platform or hosting costs. They are not falsely advertised as complete.

## Run the local foundation
Requires Python 3.11+.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn micro_helper.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/health. Run tests with `pytest`.

## Product rules
- Each person has an independent agent profile and private memory.
- Czech-first interaction and configurable personality, name and voice.
- Offline tasks stay local; online tasks are queued until connectivity returns.
- Permissions are granular. Read does not imply write, send, share or delete.
- Sensitive actions require confirmation and are auditable.
- Paired agents communicate only after both owners consent.

See `docs/` for the specification, architecture and roadmap. This is an actively rebuilt foundation, not yet a finished all-capable phone assistant.