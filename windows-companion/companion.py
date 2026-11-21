#!/usr/bin/env python3
"""Micro Helper Windows Companion using an authenticated cloud WebSocket relay."""
from __future__ import annotations

import ctypes
import json
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.request

RELAY_HTTP = "https://micro-helper-relay.onrender.com"
RELAY_WS = "wss://micro-helper-relay.onrender.com/v1/ws"
ALLOWED = {"lock", "explorer", "notepad", "calculator"}


def execute_action(action: str) -> str:
    """Execute one fixed, allowlisted Windows action. Never invokes a shell."""
    if action not in ALLOWED:
        raise ValueError("Příkaz není povolen.")
    if sys.platform != "win32":
        raise OSError("Program je určen pro Windows.")
    if action == "lock":
        if not ctypes.windll.user32.LockWorkStation():
            raise OSError("Windows se nepodařilo uzamknout.")
        return "Windows se uzamyká."
    executable = {
        "explorer": "explorer.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
    }[action]
    import subprocess
    subprocess.Popen([executable], shell=False, close_fds=True)
    return "Spuštěno: " + executable


def register_device() -> tuple[str, str]:
    """Register a short-lived pairing code and receive the desktop-only secret."""
    pairing_code = f"{secrets.randbelow(1_000_000):06d}"
    desktop_token = secrets.token_urlsafe(40)
    body = json.dumps({
        "pairing_code": pairing_code,
        "desktop_token": desktop_token,
    }).encode("utf-8")
    request = urllib.request.Request(
        RELAY_HTTP + "/v1/pair/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("registered"):
        raise RuntimeError("Cloud relay odmítl registraci notebooku.")
    return pairing_code, desktop_token


def _is_transient_registration_error(error: BaseException) -> bool:
    """Retry cold starts and network failures, but never hide TLS or client errors."""
    if isinstance(error, urllib.error.HTTPError):
        return error.code in {408, 429, 500, 502, 503, 504}
    if isinstance(error, urllib.error.URLError):
        return not isinstance(error.reason, ssl.SSLError)
    return isinstance(error, (TimeoutError, ConnectionError))


def register_device_with_retry(sleep_impl=None) -> tuple[str, str]:
    """Keep the Companion alive while a sleeping/free relay wakes up."""
    sleep = sleep_impl or time.sleep
    retry_delay = 2
    while True:
        try:
            return register_device()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if not _is_transient_registration_error(error):
                raise
            print("[Micro Helper] Relay pri parovani neni dostupny. Zkousim znovu...")
            sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)


def configure_console() -> None:
    """Use UTF-8 for Czech console messages on Windows where supported."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def serve() -> None:
    if sys.platform != "win32":
        raise SystemExit("Micro Helper Windows Companion je určen pro Windows.")
    configure_console()
    from websockets.exceptions import ConnectionClosed
    from websockets.sync.client import connect

    retry_delay = 2
    pairing_code, desktop_token = register_device_with_retry()
    print("=" * 58)
    print("MICRO HELPER · BEZPEČNÉ CLOUDOVÉ PROPOJENÍ")
    print("Párovací kód pro telefon:", pairing_code)
    print("Platnost kódu: 5 minut. Zadej ho v Micro Helperu.")
    print("Povolené akce: uzamknout, Průzkumník, Poznámkový blok, Kalkulačka.")
    print("Libovolné příkazy PowerShell/CMD nejsou podporovány.")
    print("Nech toto okno otevřené. Ctrl+C spojení ukončí.")
    print("=" * 58)

    while True:
        try:
            with connect(RELAY_WS, open_timeout=20, close_timeout=5, ping_interval=20, ping_timeout=20, max_size=16_384) as socket:
                socket.send(json.dumps({"type": "auth", "token": desktop_token}))
                print("[Micro Helper] Notebook je připojen k relay.")
                retry_delay = 2
                while True:
                    message = json.loads(socket.recv())
                    if not isinstance(message, dict) or message.get("type") != "command":
                        continue
                    request_id = str(message.get("request_id", ""))[:80]
                    action = str(message.get("action", ""))
                    try:
                        result = execute_action(action)
                        response = {"type": "result", "request_id": request_id, "ok": True, "message": result}
                        print("[Micro Helper]", result)
                    except Exception as exc:
                        response = {"type": "result", "request_id": request_id, "ok": False, "message": str(exc)[:240]}
                        print("[Micro Helper] Příkaz odmítnut nebo selhal:", str(exc)[:180])
                    socket.send(json.dumps(response, ensure_ascii=False))
        except ConnectionClosed as exc:
            if exc.code == 4401 and exc.reason == "Pairing revoked":
                print("[Micro Helper] Párování bylo zrušeno z aplikace.")
                return
            if exc.code == 4401:
                print("[Micro Helper] Relace vypršela. Vytvářím nový párovací kód…")
                pairing_code, desktop_token = register_device()
                print("[Micro Helper] Nový párovací kód:", pairing_code)
                print("Zadej nový kód v Micro Helperu.")
                retry_delay = 2
                continue
            print("[Micro Helper] Spojení přerušeno. Obnovuji…")
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            print("[Micro Helper] Relay není dostupný. Opakuji spojení…", str(exc)[:120])
        except KeyboardInterrupt:
            print("\n[Micro Helper] Spojení ukončeno.")
            return
        except Exception as exc:
            print("[Micro Helper] Neočekávaná chyba spojení:", str(exc)[:160])
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 30)


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print("\nMicro Helper ukončen.")
