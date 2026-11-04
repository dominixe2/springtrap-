# Micro Helper Windows Companion

## Run the prebuilt executable

1. Download the latest `micro-helper-windows-companion` artifact from [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/windows-companion.yml?query=branch%3Amicro-helper).
2. Extract the ZIP archive.
3. Run `MicroHelperCompanion.exe`. Python is not required for the prebuilt EXE.
4. Keep the console window open and copy the one-time pairing code into the Windows Companion panel in Micro Helper.
5. Test only the supported actions: lock Windows, open Explorer, Notepad or Calculator.

The executable is currently unsigned. Windows SmartScreen may display a warning. Only run a build downloaded from this repository's Actions artifacts.

## Run from source

Requires Python 3.11+:

```powershell
py -3 windows-companion/companion.py
```

Or run `run-companion.bat` from this folder.

## Security boundaries

- Binds only to `127.0.0.1:8765`, not Wi-Fi or the public internet.
- Accepts browser POST requests only from the official Micro Helper origin.
- Uses a random one-time pairing code and random session token. The pairing code rotates immediately after a successful pair, so the printed code cannot be reused. Restart the Companion to obtain a fresh code for a new pairing.
- Rejects repeated invalid pairing attempts.
- Allows only lock, Explorer, Notepad and Calculator.
- Does not expose arbitrary shell/PowerShell commands, arbitrary file browsing or remote desktop.
- Closing the program stops the local service and invalidates the session.

If the browser blocks local network access, allow the permission for Micro Helper. Keep the companion closed when you do not need it.
