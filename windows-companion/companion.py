#!/usr/bin/env python3
"""Micro Helper Windows Companion using an authenticated cloud WebSocket relay."""
from __future__ import annotations

import ctypes
import json
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RELAY_HTTP = "https://micro-helper-relay.onrender.com"
RELAY_WS = "wss://micro-helper-relay.onrender.com/v1/ws"
ALLOWED = {"lock", "explorer", "notepad", "calculator"}


class PairingStatus:
    """Hold the short-lived pairing code in memory only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pairing_code: str | None = None
        self._expires_at = 0.0
        self._connected = False

    def set_pairing_code(self, pairing_code: str, ttl_seconds: int) -> None:
        with self._lock:
            self._pairing_code = pairing_code
            self._expires_at = time.monotonic() + max(0, min(int(ttl_seconds), 900))

    def set_connected(self, connected: bool) -> None:
        with self._lock:
            self._connected = bool(connected)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            remaining = max(0, int(self._expires_at - time.monotonic()))
            return {
                "pairing_code": self._pairing_code if remaining > 0 else None,
                "expires_in": remaining,
                "connected": self._connected,
            }


PAIRING_STATUS_HTML = """<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Micro Helper · Bezpečné párování</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#07111f;color:#eaf2ff}
body{min-height:100vh;margin:0;display:grid;place-items:center;padding:20px;box-sizing:border-box}
main{width:min(520px,100%);padding:28px;border:1px solid #284564;border-radius:22px;background:#101d30;box-shadow:0 20px 70px #0008}
h1{font-size:24px;margin:0 0 8px}p{color:#aabbd0;line-height:1.55}
code{display:block;margin:22px 0;padding:20px;border-radius:14px;background:#07111f;color:#55e5d1;font-size:clamp(30px,9vw,48px);font-weight:800;letter-spacing:.18em;text-align:center}
#state{font-weight:650;color:#9be8d7}small{color:#8297b0}
</style>
</head>
<body>
<main>
<h1>Micro Helper · Párování telefonu</h1>
<p>Jednorázový kód je dostupný pouze na tomto notebooku. Zadej jej do panelu Windows Companion v aplikaci Micro Helper.</p>
<code id="pairingCode">Načítám…</code>
<p id="state" role="status">Kontroluji stav…</p>
<small id="expiry">Kód se po vypršení automaticky skryje. Tato stránka jej nikam neukládá.</small>
</main>
<script>
async function refreshPairingStatus(){
  const code=document.getElementById("pairingCode");
  const state=document.getElementById("state");
  const expiry=document.getElementById("expiry");
  try{
    const response=await fetch("/status",{cache:"no-store",credentials:"same-origin"});
    if(!response.ok)throw new Error("status unavailable");
    const data=await response.json();
    code.textContent=data.pairing_code||"Kód vypršel";
    state.textContent=data.connected?"Notebook je připojen k relay.":"Notebook čeká na spojení s relay.";
    expiry.textContent=data.pairing_code?"Platnost kódu: přibližně "+data.expires_in+" s.":"Restartuj Companion pro vytvoření nového kódu.";
  }catch{
    code.textContent="Nedostupné";
    state.textContent="Místní panel se nepodařilo načíst.";
  }
}
refreshPairingStatus();
setInterval(refreshPairingStatus,1000);
</script>
</body>
</html>
"""


class PairingStatusHandler(BaseHTTPRequestHandler):
    server_version = "MicroHelperPairing"
    sys_version = ""

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        port = self.server.server_port
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host", "").lower() not in allowed_hosts:
            self._send(403, "text/plain; charset=utf-8", b"Forbidden")
            return
        fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            self._send(403, "text/plain; charset=utf-8", b"Forbidden")
            return
        origin = self.headers.get("Origin")
        allowed_origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        if origin and origin not in allowed_origins:
            self._send(403, "text/plain; charset=utf-8", b"Forbidden")
            return
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", PAIRING_STATUS_HTML.encode("utf-8"))
            return
        if self.path == "/status":
            payload = json.dumps(self.server.pairing_status.snapshot(), ensure_ascii=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload)
            return
        self._send(404, "text/plain; charset=utf-8", b"Not found")

    def log_message(self, format: str, *args: object) -> None:
        # Never log pairing codes or status response details.
        return


def start_pairing_status_server(status: PairingStatus) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), PairingStatusHandler)
    server.daemon_threads = True
    server.pairing_status = status
    thread = threading.Thread(target=server.serve_forever, name="micro-helper-pairing-status", daemon=True)
    thread.start()
    return server


def pairing_status_notice(url: str) -> str:
    """Return a non-secret URL notice; the pairing code is never printed."""
    return "Párovací kód je dostupný pouze na místní stránce: " + url


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


def register_device() -> tuple[str, str, int]:
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
    expires_in = int(payload.get("expires_in", 300))
    return pairing_code, desktop_token, max(1, min(expires_in, 900))


def serve() -> None:
    if sys.platform != "win32":
        raise SystemExit("Micro Helper Windows Companion je určen pro Windows.")
    from websockets.exceptions import ConnectionClosed
    from websockets.sync.client import connect

    retry_delay = 2
    pairing_code, desktop_token, pairing_ttl = register_device()
    pairing_status = PairingStatus()
    pairing_status.set_pairing_code(pairing_code, pairing_ttl)
    status_server = start_pairing_status_server(pairing_status)
    status_url = f"http://127.0.0.1:{status_server.server_port}"
    print("=" * 58)
    print("MICRO HELPER · BEZPEČNÉ CLOUDOVÉ PROPOJENÍ")
    print(pairing_status_notice(status_url))
    print("Kód se nevypisuje do terminálu ani neukládá do souboru.")
    print("Povolené akce: uzamknout, Průzkumník, Poznámkový blok, Kalkulačka.")
    print("Libovolné příkazy PowerShell/CMD nejsou podporovány.")
    print("Nech toto okno otevřené. Ctrl+C spojení ukončí.")
    print("=" * 58)

    try:
        while True:
            try:
                with connect(RELAY_WS, open_timeout=20, close_timeout=5, ping_interval=20, ping_timeout=20, max_size=16_384) as socket:
                    socket.send(json.dumps({"type": "auth", "token": desktop_token}))
                    ready = json.loads(socket.recv())
                    if not isinstance(ready, dict) or ready.get("type") != "ready" or ready.get("role") != "desktop":
                        raise RuntimeError("Relay nepotvrdil autentizaci notebooku.")
                    pairing_status.set_connected(True)
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
                            print("[Micro Helper] Příkaz odmítnut nebo selhal:", type(exc).__name__)
                        socket.send(json.dumps(response, ensure_ascii=False))
            except ConnectionClosed as exc:
                pairing_status.set_connected(False)
                if exc.code == 4401 and exc.reason == "Pairing revoked":
                    print("[Micro Helper] Párování bylo zrušeno z aplikace.")
                    return
                if exc.code == 4401:
                    print("[Micro Helper] Relace vypršela. Obnovuji párování…")
                    try:
                        pairing_code, desktop_token, pairing_ttl = register_device()
                        pairing_status.set_pairing_code(pairing_code, pairing_ttl)
                        print("[Micro Helper] Nový kód je dostupný na místní stránce.")
                    except Exception as registration_error:
                        print("[Micro Helper] Registrace se nezdařila:", type(registration_error).__name__)
                    retry_delay = 2
                    continue
                print("[Micro Helper] Spojení přerušeno. Obnovuji…")
            except (OSError, urllib.error.URLError, TimeoutError) as exc:
                pairing_status.set_connected(False)
                print("[Micro Helper] Relay není dostupný. Opakuji spojení…", type(exc).__name__)
            except KeyboardInterrupt:
                pairing_status.set_connected(False)
                print("\n[Micro Helper] Spojení ukončeno.")
                return
            except Exception as exc:
                pairing_status.set_connected(False)
                print("[Micro Helper] Neočekávaná chyba spojení:", type(exc).__name__)
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)
    finally:
        pairing_status.set_connected(False)
        status_server.shutdown()
        status_server.server_close()


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print("\nMicro Helper ukončen.")
