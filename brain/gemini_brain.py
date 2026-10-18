"""Springtrap's Gemini-backed conversational brain.

Keep GEMINI_API_KEY outside the repository. This module uses Google's
Gemini generateContent REST endpoint and Python's standard library only.
"""
import base64
import json
import os
import urllib.error
import urllib.request
from typing import Optional

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SYSTEM_PROMPT = """Jsi Springtrap, virtuální společník na ploše Windows.
Mluvíš přirozenou češtinou, přátelsky, hravě a občas lehce sarkasticky.
Jsi stručný, ale užitečný. Nikdy netvrď, že vidíš obrazovku, pokud ti nebyl
předán její snímek. Když si nejsi jistý, řekni to. Nepředstírej ovládání
počítače ani her. Respektuj uživatelovo soukromí a pokyny k režimu nerušit.
"""

class GeminiBrainError(RuntimeError):
    """Raised when Gemini cannot be reached or returns an unusable response."""

class GeminiBrain:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        if not self.api_key:
            try:
                from key_store import load_key
                self.api_key = load_key()
            except Exception:
                self.api_key = None
        if not self.api_key:
            raise GeminiBrainError(
                "Chybí Gemini API klíč. Restartuj aplikaci a vlož ho do úvodního okna."
            )

    def ask(self, message: str, screenshot: Optional[bytes] = None,
            mime_type: str = "image/png") -> str:
        """Ask Springtrap's brain a question, optionally attaching a screenshot."""
        parts = [{"text": message}]
        if screenshot:
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(screenshot).decode("ascii"),
                }
            })

        body = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": 500},
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + self.model + ":generateContent"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise GeminiBrainError(
                f"Gemini API vrátilo HTTP {exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GeminiBrainError(f"Gemini API není dostupné: {exc}") from exc

        try:
            return "".join(
                part.get("text", "")
                for part in result["candidates"][0]["content"]["parts"]
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiBrainError(
                "Gemini vrátilo odpověď bez očekávaného textu."
            ) from exc
