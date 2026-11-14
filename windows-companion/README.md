# Micro Helper Windows Companion

## Run the prebuilt executable

1. Download the latest `micro-helper-windows-companion` artifact from [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/windows-companion.yml?query=branch%3Amicro-helper).
2. Extract the ZIP archive.
3. Run `MicroHelperCompanion.exe`. Python is not required for the prebuilt EXE.
4. Keep the console window open.
5. Open the non-secret local status URL printed in the console (127.0.0.1 only).
6. Enter the six-digit one-time pairing code shown on that local page in the Windows Companion panel in Micro Helper. The code is never printed to the terminal or written to disk.

The current staging relay is hosted on Render. It may take time to wake after inactivity; if the process restarts, launch the Companion again to generate a fresh pairing code.

## Supported actions

- Lock Windows
- Open File Explorer
- Open Notepad
- Open Calculator

No arbitrary shell/PowerShell commands, arbitrary file browsing or remote desktop are exposed.

## Security boundaries

- The Companion connects outward to the relay over HTTPS/WSS; it does not expose a listening port on the PC.
- It uses a random one-time pairing code and a separate random desktop token.
- The pairing code is held in process memory and shown only by a loopback-only status page with no-store headers; it is not written to files or logs.
- The status page rejects unexpected Host values and cross-site Fetch Metadata to reduce DNS-rebinding and cross-origin reads.
- The relay forwards only the fixed action allowlist.
- Process execution uses fixed executable names with `shell=False`.
- Closing the program stops the connection. Revoke pairing from the app when finished.

The executable is currently unsigned. Windows SmartScreen may display a warning. Only run a build downloaded from this repository's Actions artifacts.

## Run from source

Requires Python 3.11+:

```powershell
py -m pip install -r windows-companion/requirements.txt
py windows-companion/companion.py
```
