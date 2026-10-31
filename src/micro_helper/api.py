"""Local-first Micro Helper API with optional Ollama chat."""
import os
from pathlib import Path
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Micro Helper", version="0.2.0")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    model: str = Field(default="llama3.2", min_length=1, max_length=100)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


@app.get("/")
async def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "micro-helper"}


@app.get("/v1/status")
async def status():
    return {
        "product": "Micro Helper",
        "mode": "local-first",
        "implemented": ["web_chat_ui", "health", "status", "ollama_chat_adapter"],
        "not_yet_implemented": ["persistent_memory", "voice", "android_integration", "windows_worker", "agent_messaging", "animated_mascot"],
        "paid_api_required": False,
    }


@app.get("/v1/models")
async def models():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
        return {"available": True, "models": [m.get("name", "") for m in data.get("models", [])]}
    except (httpx.HTTPError, ValueError):
        return {"available": False, "models": []}


@app.post("/v1/chat")
async def chat(request: ChatRequest):
    messages = []
    for item in request.history[-20:]:
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content[:12000]})
    messages.append({"role": "user", "content": request.message})
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": request.model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
        return {"reply": data.get("message", {}).get("content", "")}
    except httpx.ConnectError:
        return {"error": "Ollama není spuštěná. Nainstaluj Ollamu, stáhni model a spusť ji. Agent zatím nemá připojený lokální jazykový model."}
    except httpx.HTTPStatusError as exc:
        return {"error": f"Ollama vrátila chybu HTTP {exc.response.status_code}. Ověř název a stažení modelu."}
    except httpx.HTTPError:
        return {"error": "Nepodařilo se spojit s lokální Ollamou."}
