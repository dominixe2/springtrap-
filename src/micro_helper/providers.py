"""Replaceable AI chat backends for Micro Helper.

Secrets are read only from process environment and are never returned by API routes.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    pass


def provider_catalog() -> list[dict[str, Any]]:
    default = os.getenv("MICRO_HELPER_PROVIDER", "ollama").strip().lower()
    return [
        {
            "id": "ollama",
            "label": "Ollama (lokálně)",
            "configured": True,
            "default": default == "ollama",
            "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
            "key_required": False,
            "privacy": "Model běží na tvém zařízení nebo vlastním serveru.",
        },
        {
            "id": "gemini",
            "label": "Google Gemini API",
            "configured": bool(os.getenv("GEMINI_API_KEY")),
            "default": default == "gemini",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "key_required": True,
            "privacy": "Zprávy se odesílají společnosti Google.",
        },
        {
            "id": "openai_compatible",
            "label": "OpenAI-compatible API",
            "configured": bool(os.getenv("OPENAI_COMPAT_BASE_URL") and os.getenv("OPENAI_COMPAT_API_KEY")),
            "default": default == "openai_compatible",
            "model": os.getenv("OPENAI_COMPAT_MODEL", "default"),
            "key_required": True,
            "privacy": "Zprávy se odesílají poskytovateli nastavenému v konfiguraci.",
        },
    ]


async def generate_chat(provider: str, model: str, messages: list[dict[str, str]]) -> str:
    provider = provider.strip().lower()
    timeout = httpx.Timeout(120.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "ollama":
                base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
                response = await client.post(
                    f"{base}/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                )
                response.raise_for_status()
                result = response.json().get("message", {}).get("content", "")
            elif provider == "gemini":
                key = os.getenv("GEMINI_API_KEY")
                if not key:
                    raise ProviderConfigurationError("Chybí GEMINI_API_KEY.")
                model_id = model.removeprefix("models/")
                contents = []
                system_parts = []
                for item in messages:
                    role, content = item.get("role"), item.get("content", "")
                    if role == "system":
                        system_parts.append(content)
                    else:
                        contents.append({
                            "role": "model" if role == "assistant" else "user",
                            "parts": [{"text": content}],
                        })
                payload: dict[str, Any] = {"contents": contents}
                if system_parts:
                    payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
                    params={"key": key},
                    json=payload,
                )
                response.raise_for_status()
                candidates = response.json().get("candidates", [])
                result = "".join(
                    part.get("text", "")
                    for part in (candidates[0].get("content", {}).get("parts", []) if candidates else [])
                )
            elif provider == "openai_compatible":
                base = os.getenv("OPENAI_COMPAT_BASE_URL", "").strip().rstrip("/")
                key = os.getenv("OPENAI_COMPAT_API_KEY")
                if not base or not key:
                    raise ProviderConfigurationError(
                        "Nastav OPENAI_COMPAT_BASE_URL a OPENAI_COMPAT_API_KEY."
                    )
                endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
                response = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "messages": messages, "stream": False},
                )
                response.raise_for_status()
                result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                raise ProviderConfigurationError(f"Neznámý poskytovatel: {provider}")
    except ProviderConfigurationError:
        raise
    except httpx.HTTPStatusError as exc:
        raise ProviderRequestError(f"Poskytovatel vrátil HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ProviderRequestError("Nepodařilo se spojit s AI poskytovatelem nebo přečíst jeho odpověď.") from exc

    if not isinstance(result, str) or not result.strip():
        raise ProviderRequestError("Model vrátil prázdnou odpověď.")
    return result.strip()
