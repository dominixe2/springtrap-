@echo off
cd /d "%~dp0"
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m uvicorn micro_helper.api:app --app-dir src --host 127.0.0.1 --port 8000
pause
