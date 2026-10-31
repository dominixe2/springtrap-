"""Minimal local API foundation for Micro Helper."""
from fastapi import FastAPI

app = FastAPI(title="Micro Helper", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "micro-helper"}


@app.get("/v1/status")
async def status():
    return {
        "product": "Micro Helper",
        "mode": "local-foundation",
        "implemented": ["health", "status"],
        "not_yet_implemented": [
            "llm_chat", "persistent_memory", "voice", "android_integration",
            "windows_worker", "agent_messaging", "animated_mascot"
        ],
        "paid_api_required": False,
    }
