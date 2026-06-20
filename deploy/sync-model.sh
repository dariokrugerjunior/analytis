#!/usr/bin/env bash
# Sync a trained model from the local DB+filesystem to the production VM.
#
# Workflow:
#   1. Query the local model_version row by name
#   2. Upload the .pkl artifact to the VM
#   3. docker cp the .pkl into the analytis-app container (lands in the models volume)
#   4. Run an UPSERT into the production model_version table (ON CONFLICT (name))
#
# Usage:
#   ./deploy/sync-model.sh <model-name>
#   ./deploy/sync-model.sh xgb-1x2-v1

set -euo pipefail

NAME="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/deploy"

log()  { printf "\033[1;34m[sync-model]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

[[ -n "$NAME" ]] || die "Usage: $0 <model-name>"

VM_IP="${VM_IP:-$(cat "$DEPLOY_DIR/.vm-ip" 2>/dev/null || true)}"
[[ -n "$VM_IP" ]] || die "VM_IP not set."
REMOTE="ubuntu@${VM_IP}"

LOCAL_PG="analytis-postgres"
docker ps --format '{{.Names}}' | grep -q "^${LOCAL_PG}$" \
  || die "Local container ${LOCAL_PG} not running. Start docker-compose.yml first."

# ============================================================
# 1. Pull artifact_path + generate UPSERT SQL from local DB
# ============================================================
log "Querying local model_version row: $NAME"

RAW_ARTIFACT_PATH=$(docker exec -i "$LOCAL_PG" psql -U analytis -d analytis -t -A -c \
  "SELECT artifact_path FROM model_version WHERE name='$NAME'")
[[ -n "$RAW_ARTIFACT_PATH" ]] || die "Model '$NAME' not found in local DB."

# Normalize Windows backslashes → forward slashes (POSIX, VM-compatible)
ARTIFACT_PATH="${RAW_ARTIFACT_PATH//\\//}"

LOCAL_ARTIFACT="$REPO_ROOT/$ARTIFACT_PATH"
[[ -f "$LOCAL_ARTIFACT" ]] || die "Local artifact missing: $LOCAL_ARTIFACT"

# If the path in DB had backslashes, fix it locally first so future operations match
if [[ "$RAW_ARTIFACT_PATH" != "$ARTIFACT_PATH" ]]; then
  log "Normalizing artifact_path in local DB ($RAW_ARTIFACT_PATH → $ARTIFACT_PATH)"
  docker exec -i "$LOCAL_PG" psql -U analytis -d analytis -c \
    "UPDATE model_version SET artifact_path='$ARTIFACT_PATH' WHERE name='$NAME'" >/dev/null
fi
SIZE=$(du -h "$LOCAL_ARTIFACT" | cut -f1)
log "Found artifact $ARTIFACT_PATH ($SIZE)"

# Build idempotent UPSERT — preserves the local UUID so artifact_path
# (which embeds the id) stays consistent.
UPSERT_SQL=$(docker exec -i "$LOCAL_PG" psql -U analytis -d analytis -t -A -c "
SELECT format(
  E'INSERT INTO model_version (id, name, family, git_sha, hyperparams, metrics, artifact_path, trained_at, is_promoted) '
  'VALUES (%L, %L, %L, %L, %L::jsonb, %L::jsonb, %L, %L, %L) '
  'ON CONFLICT (name) DO UPDATE SET '
  'id=EXCLUDED.id, family=EXCLUDED.family, git_sha=EXCLUDED.git_sha, '
  'hyperparams=EXCLUDED.hyperparams, metrics=EXCLUDED.metrics, '
  'artifact_path=EXCLUDED.artifact_path, trained_at=EXCLUDED.trained_at, '
  'updated_at=NOW();',
  id, name, family, git_sha, hyperparams::text, metrics::text,
  artifact_path, trained_at, is_promoted
)
FROM model_version WHERE name = '$NAME'
")

[[ -n "$UPSERT_SQL" ]] || die "Failed to generate UPSERT SQL"

# ============================================================
# 2. Ship artifact + SQL to VM
# ============================================================
log "Uploading artifact to VM..."
scp -q "$LOCAL_ARTIFACT" "$REMOTE:/tmp/sync-$NAME.pkl"

log "Uploading UPSERT SQL..."
printf '%s\n' "$UPSERT_SQL" | ssh "$REMOTE" "cat > /tmp/sync-$NAME.sql"

# ============================================================
# 3. Apply on VM: docker cp .pkl + psql UPSERT
# ============================================================
log "Applying on VM (docker cp + DB upsert)..."
ssh "$REMOTE" "bash -s" <<EOF
set -e
sudo docker cp /tmp/sync-$NAME.pkl analytis-app:/app/$ARTIFACT_PATH
cat /tmp/sync-$NAME.sql | sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml --env-file /opt/analytis/deploy/.env.prod exec -T postgres psql -U analytis -d analytis
rm /tmp/sync-$NAME.pkl /tmp/sync-$NAME.sql
EOF

log "Verifying on VM..."
ssh "$REMOTE" "sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml --env-file /opt/analytis/deploy/.env.prod exec -T postgres psql -U analytis -d analytis -c \"SELECT name, family, trained_at FROM model_version WHERE name='$NAME'\""

log "Done. Model '$NAME' synced."
