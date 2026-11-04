#!/usr/bin/env python3
"""Micro Helper Windows Companion. Loopback-only, paired, fixed-command bridge."""
from __future__ import annotations
import ctypes, json, secrets, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_ORIGIN = "https://micro-helper-ygeuyn.v2.appdeploy.ai"
HOST, PORT = "127.0.0.1", 8765
PAIRING_CODE = secrets.token_urlsafe(8)
SESSION_TOKEN = ""
FAILED_PAIRS = 0
PAIR_LOCK = threading.Lock()
ALLOWED = {"lock", "explorer", "notepad", "calculator"}

class Handler(BaseHTTPRequestHandler):
    server_version = "MicroHelperCompanion/1.0"
    def log_message(self, fmt, *args): print("[Micro Helper]", fmt % args)
    def _cors(self):
        if self.headers.get("Origin", "") == APP_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", APP_ORIGIN)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
    def _send(self, status, payload):
        raw=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store")
        self._cors(); self.end_headers(); self.wfile.write(raw)
    def _origin_ok(self): return self.headers.get("Origin","") == APP_ORIGIN
    def do_OPTIONS(self):
        if not self._origin_ok(): self.send_error(403); return
        self.send_response(204); self._cors(); self.send_header("Content-Length","0"); self.end_headers()
    def do_GET(self):
        if self.path != "/health": self._send(404,{"detail":"Not found"}); return
        self._send(200,{"ready":True,"name":"Micro Helper Windows Companion"})
    def do_POST(self):
        global PAIRING_CODE, SESSION_TOKEN, FAILED_PAIRS
        if not self._origin_ok(): self._send(403,{"detail":"Původ požadavku není povolen."}); return
        if self.client_address[0] not in ("127.0.0.1","::1"):
            self._send(403,{"detail":"Přístup je povolen pouze z tohoto počítače."}); return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length<2 or length>4096: self._send(413,{"detail":"Neplatná velikost požadavku."}); return
            payload=json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                self._send(400,{"detail":"JSON požadavek musí být objekt."}); return
        except Exception: self._send(400,{"detail":"Neplatný JSON požadavek."}); return
        if self.path=="/pair":
            with PAIR_LOCK:
                if FAILED_PAIRS>=8: self._send(429,{"detail":"Příliš mnoho pokusů. Restartuj doprovodný program."}); return
                if not secrets.compare_digest(str(payload.get("code","")),PAIRING_CODE):
                    FAILED_PAIRS+=1; self._send(401,{"detail":"Párovací kód nesouhlasí."}); return
                SESSION_TOKEN=secrets.token_urlsafe(32); PAIRING_CODE=secrets.token_urlsafe(8); FAILED_PAIRS=0
                self._send(200,{"paired":True,"token":SESSION_TOKEN})
                print("[Micro Helper] Nové párování dokončeno.")
            return
        if self.path not in ("/command", "/unpair"): self._send(404,{"detail":"Neznámá akce."}); return
        supplied=self.headers.get("Authorization","")
        if not SESSION_TOKEN or not secrets.compare_digest(supplied,"Bearer "+SESSION_TOKEN):
            self._send(401,{"detail":"Relace vypršela. Spáruj notebook znovu."}); return
        if self.path == "/unpair":
            SESSION_TOKEN = ""
            self._send(200, {"unpaired": True, "message": "Relace notebooku byla zrušena."})
            return
        action=str(payload.get("action",""))
        if action not in ALLOWED: self._send(403,{"detail":"Tento příkaz není povolen."}); return
        try:
            if sys.platform!="win32": self._send(501,{"detail":"Program je určen pro Windows."}); return
            if action=="lock":
                ctypes.windll.user32.LockWorkStation(); message="Windows se uzamyká."
            else:
                executable={"explorer":"explorer.exe","notepad":"notepad.exe","calculator":"calc.exe"}[action]
                subprocess.Popen([executable],shell=False,close_fds=True); message="Spuštěno: "+executable
            self._send(200,{"ok":True,"message":message})
        except Exception as exc: self._send(500,{"detail":"Příkaz se nepodařilo provést: "+str(exc)[:180]})
    def do_PUT(self): self._send(405,{"detail":"Metoda není povolena."})
    def do_DELETE(self): self._send(405,{"detail":"Metoda není povolena."})

if __name__=="__main__":
    if sys.platform!="win32": print("Tento program je určen pro Windows."); raise SystemExit(1)
    print("="*54); print("MICRO HELPER WINDOWS COMPANION")
    print("Pouze místní adresa 127.0.0.1. Párovací kód:")
    print(PAIRING_CODE); print("Nech toto okno otevřené. Zavřením se relace zruší."); print("="*54)
    try: ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
    except OSError as exc: print("Nelze spustit místní službu:",exc); input("Stiskni Enter pro zavření…")
