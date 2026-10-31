#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo "Micro Helper · instalace pro Android / Termux"
pkg update -y
pkg install -y python git
python -m pip install --upgrade pip

if [ ! -d "$HOME/springtrap-" ]; then
  git clone --depth 1 --branch main https://github.com/dominixe2/springtrap-.git "$HOME/springtrap-"
else
  git -C "$HOME/springtrap-" pull --ff-only
fi

cd "$HOME/springtrap-"
python -m pip install -e .
mkdir -p "$HOME/.micro-helper"
echo
echo "Instalace hotová. Spusť: bash ~/springtrap-/termux-start.sh"
