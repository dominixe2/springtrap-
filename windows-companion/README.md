# Micro Helper Windows Companion

1. Install Python 3 for Windows from https://www.python.org/downloads/windows/ and enable **Add Python to PATH**.
2. Keep `companion.py` and `run-companion.bat` in the same folder.
3. Run `run-companion.bat` and keep its window open.
4. Copy the one-time pairing code shown in the terminal into the Windows Companion panel in Micro Helper.

## Security boundaries
- Binds only to `127.0.0.1`, not Wi-Fi or the public internet.
- Accepts browser requests only from the official Micro Helper origin.
- Uses a random one-time pairing code and a random session token; both reset when the program restarts.
- Allows only lock, Explorer, Notepad and Calculator actions.
- Does not expose arbitrary shell, PowerShell, file browsing or remote desktop.
- Closing the terminal stops the service.

If the browser blocks local network access, allow the permission for Micro Helper. The helper uses port 8765.
