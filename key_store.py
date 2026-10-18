"""User-scoped Windows DPAPI storage for the Gemini API key."""
import ctypes
import os
from ctypes import wintypes
from pathlib import Path

APP_DATA = Path(os.environ.get("APPDATA", str(Path.home()))) / "Springtrap"
KEY_FILE = APP_DATA / "gemini-key.dpapi"

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return blob, buffer

def _protect(data: bytes) -> bytes:
    source, keepalive = _blob(data)
    output = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(ctypes.byref(source), "Springtrap Gemini API key",
                                    None, None, None, 0, ctypes.byref(output)):
        raise OSError("Windows se nepodařilo zašifrovat API klíč.")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)

def _unprotect(data: bytes) -> bytes:
    source, keepalive = _blob(data)
    output = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0,
                                      ctypes.byref(output)):
        raise OSError("Uložený klíč nejde dešifrovat. Zadej ho prosím znovu.")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)

def load_key():
    """Return the key decrypted for the current Windows user, or None."""
    if os.name != "nt" or not KEY_FILE.exists():
        return None
    try:
        value = _unprotect(KEY_FILE.read_bytes()).decode("utf-8").strip()
        return value or None
    except (OSError, UnicodeError):
        return None

def save_key(api_key: str):
    """Encrypt the key using Windows DPAPI, bound to the current Windows user."""
    if os.name != "nt":
        raise OSError("Bezpečné ukládání klíče je podporováno pouze ve Windows.")
    value = api_key.strip()
    if not value:
        raise ValueError("API klíč nesmí být prázdný.")
    APP_DATA.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(_protect(value.encode("utf-8")))
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
