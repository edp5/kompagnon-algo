#!/bin/zsh

set -euo pipefail

error() {
  echo "Erreur: $1" >&2
  exit 1
}

echo "============================"

echo "Configure virtual environment"
command -v python3 >/dev/null 2>&1 || error "python3 est introuvable"
python3 -m venv .venv
[[ -f ".venv/bin/activate" ]] || error "activation du virtualenv impossible (.venv/bin/activate manquant)"
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies"
[[ -f "requirements.txt" ]] || error "requirements.txt est introuvable"
python -m pip install -r requirements.txt

echo "============================"