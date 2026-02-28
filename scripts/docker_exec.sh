#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${1:-contextual-assistant}"
shift || true

if [[ "$#" -gt 0 ]]; then
  docker exec -it "$CONTAINER_NAME" "$@"
else
  docker exec -it "$CONTAINER_NAME" sh
fi
