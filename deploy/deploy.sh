#!/usr/bin/env bash
# Local-build deploy strategy — the VM is too small (1 GB RAM) to build the
# frontend, so we build the image LOCALLY, save to tar, scp, and `docker load`
# on the remote.
#
# Used for first deploy AND subsequent updates.
#
# Usage:
#   ./deploy/deploy.sh                  # uses deploy/.vm-ip
#   VM_IP=1.2.3.4 ./deploy/deploy.sh    # explicit override

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/deploy"
IMAGE_TAG="analytis-app:latest"
IMAGE_TAR="/tmp/analytis-app.tar.gz"

log()  { printf "\033[1;34m[deploy]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

VM_IP="${VM_IP:-$(cat "$DEPLOY_DIR/.vm-ip" 2>/dev/null || true)}"
[[ -n "$VM_IP" ]] || die "VM_IP not set. Run provision-oci.sh first or pass VM_IP=<ip>."

REMOTE="ubuntu@${VM_IP}"
REMOTE_DIR="/opt/analytis"

command -v docker >/dev/null || die "docker not installed."
[[ -f "$DEPLOY_DIR/.env.prod" ]] || die "deploy/.env.prod missing. Copy .env.prod.example and fill in."

log "Target: $REMOTE:$REMOTE_DIR"

# ============================================================
# 1. Build image locally (multi-stage: node → python with frontend baked in)
# ============================================================
log "Building $IMAGE_TAG locally (may take 3-5 min on first run)..."
cd "$REPO_ROOT"
docker build -f deploy/Dockerfile.app -t "$IMAGE_TAG" .

# ============================================================
# 2. Save + compress image
# ============================================================
log "Exporting image to $IMAGE_TAR..."
docker save "$IMAGE_TAG" | gzip -1 > "$IMAGE_TAR"
SIZE=$(du -h "$IMAGE_TAR" | cut -f1)
log "Archive size: $SIZE"

# ============================================================
# 3. Upload image + config files to VM
# ============================================================
log "Uploading image (this is the slow step on residential upload) ..."
scp -q "$IMAGE_TAR" "$REMOTE:$REMOTE_DIR/deploy/"

log "Uploading compose + nginx + finish.sh + .env.prod ..."
scp -q "$DEPLOY_DIR/docker-compose.prod.yml" "$REMOTE:$REMOTE_DIR/deploy/"
scp -q "$DEPLOY_DIR/nginx/default.conf.template" "$REMOTE:$REMOTE_DIR/deploy/nginx/"
scp -q "$DEPLOY_DIR/finish.sh" "$REMOTE:$REMOTE_DIR/deploy/"
scp -q "$DEPLOY_DIR/backup/pg-backup.sh" "$REMOTE:$REMOTE_DIR/deploy/backup/" 2>/dev/null \
  || ssh "$REMOTE" "mkdir -p $REMOTE_DIR/deploy/backup" && \
     scp -q "$DEPLOY_DIR/backup/pg-backup.sh" "$REMOTE:$REMOTE_DIR/deploy/backup/"
scp -q "$DEPLOY_DIR/.env.prod" "$REMOTE:$REMOTE_DIR/deploy/.env.prod"

# Migrations also need to be present on the VM for `alembic upgrade head`
log "Uploading alembic.ini + migrations/ ..."
scp -q "$REPO_ROOT/alembic.ini" "$REMOTE:$REMOTE_DIR/"
rsync -az --delete "$REPO_ROOT/migrations/" "$REMOTE:$REMOTE_DIR/migrations/" 2>/dev/null \
  || scp -rq "$REPO_ROOT/migrations" "$REMOTE:$REMOTE_DIR/"

# ============================================================
# 4. Run finish.sh remotely (docker load → certbot → compose up → migrate)
# ============================================================
log "Running finish.sh on VM..."
ssh -t "$REMOTE" "chmod +x $REMOTE_DIR/deploy/*.sh $REMOTE_DIR/deploy/backup/*.sh && bash $REMOTE_DIR/deploy/finish.sh"

# Clean up local tarball
rm -f "$IMAGE_TAR"
log "Done."
