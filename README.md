# Micro Helper

Free-first, local-first personal AI agent for Android and Windows.

**Springtrap is removed as the product.** The old desktop character app is being replaced. An original animated mascot may later be selected as an optional appearance only; it is never the agent's brain or identity.

## Cost model

- No paid API key or subscription is required for the local core.
- The first runnable version uses a local backend and browser UI.
- For AI replies, connect a local model through [Ollama](https://ollama.com/). This uses the computer's resources rather than a paid API.
- Cloud hosting, remote access and mobile-network services may have costs; they are optional and are not represented as free.

## Run locally

Requires Python 3.11+.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn micro_helper.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The health endpoint is http://127.0.0.1:8000/health.

Run tests with `pytest`.

## Current scope

The local foundation and truthful capability reporting come first. Voice, Android integration, Windows automation, long-term memory, paired agents and animated mascots are staged features, not falsely advertised as finished.
