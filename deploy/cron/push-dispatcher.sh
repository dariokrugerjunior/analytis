#!/usr/bin/env bash
# Per-minute cron: dispatches pre/post-match push notifications via the analytis CLI.
set -euo pipefail

REPO_ROOT="/opt/analytis"
LOG_DIR="$REPO_ROOT/logs"
LOG="$LOG_DIR/push-dispatcher.log"
LOCK="/tmp/analytis-push-dispatcher.lock"

mkdir -p "$LOG_DIR"

exec 9>"$LOCK"
flock -n 9 || exit 0

{
  echo "=== $(date -u +%FT%TZ) push-dispatch start ==="
  docker compose -f "$REPO_ROOT/deploy/docker-compose.prod.yml" \
    --env-file "$REPO_ROOT/deploy/.env.prod" \
    exec -T app analytis push dispatch
  echo "=== $(date -u +%FT%TZ) push-dispatch done ==="
} >> "$LOG" 2>&1
