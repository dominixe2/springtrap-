#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/springtrap-"
echo "Micro Helper běží pouze na tomto telefonu."
echo "Otevři v Chrome: http://127.0.0.1:8000"
echo "Zastavení: Ctrl+C v Termuxu."
exec python -m uvicorn micro_helper.api:app --app-dir src --host 127.0.0.1 --port 8000
