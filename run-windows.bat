@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if not exist ".venv\\Scripts\\python.exe" (
  echo Creating the Micro Helper environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)

call .venv\\Scripts\\activate.bat
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is required. Install it and remove the .venv folder before retrying.
  goto :error
)

echo Installing or updating Micro Helper...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -e .
if errorlevel 1 goto :error

echo.
echo Micro Helper will open at http://127.0.0.1:8000
echo Keep this window open while using the app. Press Ctrl+C to stop it.
start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"
python -m uvicorn micro_helper.api:app --app-dir src --host 127.0.0.1 --port 8000
goto :eof

:error
echo.
echo Installation failed. Read the error above, then try again.
pause
exit /b 1
