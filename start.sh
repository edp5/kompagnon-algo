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
    echo "Error: PORT must be set. Define PORT in the environment or add it to the .env file."
    exit 1
fi
echo "Started server on port $PORT..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port "$PORT"
