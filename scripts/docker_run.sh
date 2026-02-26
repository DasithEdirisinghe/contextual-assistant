#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-contextual-assistant:latest}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.docker}"

if [[ "${1:-}" == "--help" ]]; then
  cat <<EOF
Usage:
  scripts/docker_run.sh [command...]

Runs contextual-assistant container using:
  --env-file .env.docker
  host Ollama endpoint mapping
  mounted data directory (DB path comes from DATABASE_URL)

Examples:
  scripts/docker_run.sh
  scripts/docker_run.sh python -m assistant.interfaces.cli.app thinking-run
EOF
  exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Create it from .env.docker template."
  exit 1
fi

mkdir -p "$ROOT_DIR/data"

cd "$ROOT_DIR"

if [[ "$#" -gt 0 ]]; then
  docker run --rm -it \
    --env-file "$ENV_FILE" \
    --add-host=host.docker.internal:host-gateway \
    -v "$ROOT_DIR/data:/app/data" \
    "$IMAGE_NAME" "$@"
else
  docker run --rm -it \
    --env-file "$ENV_FILE" \
    --add-host=host.docker.internal:host-gateway \
    -v "$ROOT_DIR/data:/app/data" \
    "$IMAGE_NAME"
fi
