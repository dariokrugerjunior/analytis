#!/usr/bin/env bash
# Daily Postgres backup. Cron-installed by finish.sh (runs as ubuntu, 04:30 UTC).
# Retention: 7 daily + 4 weekly (Sunday).
#
# TODO: upgrade to OCI Object Storage upload via `oci os object put` for off-host backup.
#       Requires: oci-cli installed on VM + bucket pre-created + instance principal auth.

set -euo pipefail

REPO_ROOT="/opt/analytis"
BACKUP_DIR="$REPO_ROOT/backups"
COMPOSE_FILE="$REPO_ROOT/deploy/docker-compose.prod.yml"
ENV_FILE="$REPO_ROOT/deploy/.env.prod"

mkdir -p "$BACKUP_DIR"

DATE="$(date -u +%Y%m%d)"
DOW="$(date -u +%u)"   # 1 (Mon) .. 7 (Sun)
DAILY_FILE="$BACKUP_DIR/analytis-daily-${DATE}.sql.gz"

# Dump from the postgres container — no need to expose port to host
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  pg_dump -U analytis -d analytis --no-owner --no-privileges \
  | gzip -9 > "$DAILY_FILE"

echo "[backup] daily: $DAILY_FILE ($(du -h "$DAILY_FILE" | cut -f1))"

# Sunday → also keep as weekly snapshot
if [[ "$DOW" == "7" ]]; then
  WEEKLY_FILE="$BACKUP_DIR/analytis-weekly-${DATE}.sql.gz"
  cp "$DAILY_FILE" "$WEEKLY_FILE"
  echo "[backup] weekly: $WEEKLY_FILE"
fi

# Rotation: keep 7 most recent dailies + 4 most recent weeklies
find "$BACKUP_DIR" -name 'analytis-daily-*.sql.gz' -type f \
  | sort -r | tail -n +8 | xargs -r rm -f
find "$BACKUP_DIR" -name 'analytis-weekly-*.sql.gz' -type f \
  | sort -r | tail -n +5 | xargs -r rm -f

echo "[backup] rotation complete"
