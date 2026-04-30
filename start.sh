#!/bin/bash
set -e

SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR" || { echo "Erreur: Impossible d'accéder au répertoire du script"; exit 1; }

if [ -f ".env" ]; then
    set -a
    . ".env"
    set +a
fi

if [ -z "$PORT" ]; then
    echo "Error, environment is not define"
    exit 1
fi
echo "Started server on port $PORT..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port "$PORT"
