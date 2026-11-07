from __future__ import annotations

import os
import httpx
from micro_helper.orchestration import AgentTask


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or os.getenv("MICRO_HELPER_MODEL", "llama3.2")
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")

    async def complete(self, task: AgentTask, shared_context: str) -> str:
        messages = [
            {"role": "system", "content": "Jsi pracovní agent Micro Helperu. Odpovídej česky. Neprováděj externí akce."},
            {"role": "user", "content": f"Kontext:\n{shared_context[:12000]}\nÚkol: {task.title}\n{task.instructions}"},
        ]
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self.base_url}/api/chat", json={"model": self.model, "messages": messages, "stream": False})
            response.raise_for_status()
            result = response.json().get("message", {}).get("content", "")
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Ollama returned an empty response")
        return result.strip()

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                names = [item.get("name", "") for item in response.json().get("models", [])]
            return any(name == self.model or name.split(":")[0] == self.model.split(":")[0] for name in names)
        except (httpx.HTTPError, ValueError):
            return False


def available_local_providers() -> list[OllamaProvider]:
    return [OllamaProvider()]
