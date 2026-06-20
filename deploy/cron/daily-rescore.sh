#!/usr/bin/env bash
# Daily re-ingest fixtures + re-score upcoming Copa 2026 matches.
# Installed by deploy/finish.sh as /etc/cron.d/analytis-rescore.
# Logs append to /opt/analytis/logs/daily-rescore.log (rotated by logrotate elsewhere).
#
# Manual run:  sudo /opt/analytis/deploy/cron/daily-rescore.sh

set -euo pipefail

REPO_ROOT="/opt/analytis"
LOG_DIR="$REPO_ROOT/logs"
LOG="$LOG_DIR/daily-rescore.log"
COMPOSE="docker compose -f $REPO_ROOT/deploy/docker-compose.prod.yml --env-file $REPO_ROOT/deploy/.env.prod"

mkdir -p "$LOG_DIR"
exec >> "$LOG" 2>&1
echo
echo "=== $(date -u +%FT%TZ) daily-rescore starting ==="

# 1. Re-ingest fixtures (picks up stage transitions as Copa progresses)
echo "--- ingest fixtures ---"
$COMPOSE exec -T app analytis ingest fixtures --competition 2000 --season 2026 || \
  echo "WARN: ingest fixtures failed (non-fatal, continuing)"

# 2. Get scheduled upcoming match IDs
echo "--- listing upcoming matches ---"
MATCH_IDS=$($COMPOSE exec -T postgres psql -U analytis -d analytis -t -A -c \
  "SELECT id FROM match WHERE status='scheduled' AND kickoff_utc > NOW() ORDER BY kickoff_utc" \
  | tr -d '\r' | grep -v '^$' || true)
COUNT=$(echo "$MATCH_IDS" | wc -l)
echo "found $COUNT scheduled upcoming match(es)"

# 3. Re-score each with the ensemble (dc-v1-no-decay + xgb-1x2-v1, 50/50)
OK=0
FAIL=0
for id in $MATCH_IDS; do
  [[ -z "$id" ]] && continue
  if $COMPOSE exec -T app analytis score ensemble \
      --match-id "$id" \
      --dc-model dc-v1-no-decay \
      --xgb-model xgb-1x2-v1 \
      --ensemble-name ensemble-v1 \
      --dc-weight 0.5 --xgb-weight 0.5 > /dev/null 2>&1; then
    OK=$((OK + 1))
  else
    FAIL=$((FAIL + 1))
  fi
done
echo "ensemble re-score: $OK OK, $FAIL failed"

echo "=== $(date -u +%FT%TZ) daily-rescore done ==="
