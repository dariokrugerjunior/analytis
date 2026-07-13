#!/usr/bin/env bash
# Runs ON THE VM. Issues TLS cert, brings docker stack up, runs migrations.
# Idempotent — safe to re-run after the first invocation (won't re-issue cert
# if already valid; certbot will report "Certificate not yet due for renewal").

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DEPLOY_DIR"

log()  { printf "\033[1;34m[finish]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

# ============================================================
# Sanity checks
# ============================================================
[[ -f /opt/analytis/.cloud-init-done ]] || die "cloud-init has not finished yet. Wait ~3 min after VM launch."
[[ -f ".env.prod" ]] || die ".env.prod missing. Run: scp deploy/.env.prod ubuntu@<ip>:/opt/analytis/deploy/.env.prod"
[[ -f "analytis-app.tar.gz" ]] || die "analytis-app.tar.gz missing. Re-run deploy.sh from local machine."

# Load DOMAIN and ACME_EMAIL from .env.prod
set -a; source .env.prod; set +a
[[ -n "${DOMAIN:-}" ]] || die "DOMAIN missing in .env.prod"
[[ -n "${ACME_EMAIL:-}" ]] || die "ACME_EMAIL missing in .env.prod"

log "Domain: $DOMAIN"
log "ACME email: $ACME_EMAIL"

# DNS sanity — does the domain resolve to this VM's public IP?
VM_IP="$(curl -fsS https://api.ipify.org)"
DNS_IP="$(dig +short "$DOMAIN" | tail -n1)"
if [[ "$VM_IP" != "$DNS_IP" ]]; then
  printf "\033[1;33m[warn]\033[0m DNS mismatch: %s resolves to '%s' but VM IP is '%s'\n" "$DOMAIN" "$DNS_IP" "$VM_IP"
  printf "\033[1;33m[warn]\033[0m Update your DNS A-record and wait for propagation. Continue anyway? [y/N] "
  read -r ans
  [[ "$ans" =~ ^[Yy]$ ]] || exit 1
fi

# ============================================================
# TLS — Let's Encrypt via standalone (port 80 must be free)
# ============================================================
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
if [[ -f "$CERT_PATH" ]]; then
  log "Certificate already present at $CERT_PATH — skipping issuance."
else
  log "Issuing Let's Encrypt certificate via standalone (binds to port 80)..."
  # Make sure nothing is on port 80
  sudo docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
  sudo certbot certonly --standalone \
    -d "$DOMAIN" --email "$ACME_EMAIL" \
    --agree-tos --no-eff-email -n
fi

# ============================================================
# Load image + bring stack up (no build — the VM is too small to build)
# ============================================================
log "Loading docker image from analytis-app.tar.gz..."
sudo docker load < analytis-app.tar.gz

log "Starting stack..."
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

log "Waiting for postgres to be healthy..."
for i in {1..30}; do
  if sudo docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres pg_isready -U analytis -d analytis >/dev/null 2>&1; then
    log "Postgres ready."
    break
  fi
  sleep 2
done

log "Running migrations..."
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T app uv run analytis db migrate

# ============================================================
# Smoke tests
# ============================================================
log "Smoke test: GET https://$DOMAIN/v1/health"
for i in {1..15}; do
  if curl -fsS "https://$DOMAIN/v1/health" >/dev/null; then
    log "Health endpoint OK."
    break
  fi
  sleep 2
done

curl -fsS "https://$DOMAIN/v1/health"; echo
curl -fsS "https://$DOMAIN/v1/models" | head -c 200; echo

# ============================================================
# Setup cron: TLS renewal + nightly backup
# ============================================================
log "Installing cron jobs (TLS renew, daily backup, daily re-score)..."
sudo tee /etc/cron.d/analytis-renew >/dev/null <<EOF
0 3 * * * root certbot renew --quiet --deploy-hook "docker compose -f /opt/analytis/deploy/docker-compose.prod.yml exec -T nginx nginx -s reload"
EOF

sudo tee /etc/cron.d/analytis-backup >/dev/null <<EOF
30 4 * * * ubuntu /opt/analytis/deploy/backup/pg-backup.sh
EOF

# Daily 07:00 UTC = 04:00 BRT, off-peak. Re-ingests fixtures + re-scores upcoming
# matches with ensemble-v1 (dc-v1-no-decay + xgb-1x2-v1, 50/50).
sudo chmod +x /opt/analytis/deploy/cron/daily-rescore.sh
sudo tee /etc/cron.d/analytis-rescore >/dev/null <<EOF
0 7 * * * root /opt/analytis/deploy/cron/daily-rescore.sh
EOF

sudo chmod +x /opt/analytis/deploy/cron/push-dispatcher.sh
sudo tee /etc/cron.d/analytis-push >/dev/null <<EOF
* * * * * root /opt/analytis/deploy/cron/push-dispatcher.sh
EOF

cat <<EOF

╔══════════════════════════════════════════════════════════════╗
║  DEPLOY COMPLETE                                             ║
╠══════════════════════════════════════════════════════════════╣
║  App:        https://$DOMAIN
║  Health:     https://$DOMAIN/v1/health
║  Docs:       https://$DOMAIN/docs
║
║  Logs:       sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml logs -f
║  Backup:     /opt/analytis/backups/ (daily 04:30 UTC)
║  TLS renew:  daily 03:00 UTC (cron + certbot --deploy-hook)
╚══════════════════════════════════════════════════════════════╝
EOF
