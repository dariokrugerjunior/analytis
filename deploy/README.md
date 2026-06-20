# deploy/

Production deploy artifacts for **Oracle Cloud Infrastructure** (Ampere A1 Always Free).

Full architecture and reasoning: **[`docs/deploy-oracle-cloud.md`](../docs/deploy-oracle-cloud.md)**.

## Files

| File | Purpose |
|---|---|
| `Dockerfile.app` | Multi-stage: node builds frontend → python:3.12-slim with uv |
| `Dockerfile.app.dockerignore` | Excludes cruft from build context |
| `docker-compose.prod.yml` | postgres + app + nginx (TLS) |
| `.env.prod.example` | Template for production env vars — copy to `.env.prod` |
| `nginx/default.conf.template` | Reverse proxy + TLS, uses `${DOMAIN}` envsubst |
| `cloud-init.yaml` | First-boot bootstrap (docker, certbot, firewall) |
| `provision-oci.sh` | Provisions OCI infra via `oci-cli` |
| `deploy.sh` | Local: rsync + scp + ssh finish.sh |
| `finish.sh` | Remote: certbot + compose up + migrations |
| `backup/pg-backup.sh` | Daily Postgres dump with 7d/4w rotation |

## Quickstart (first deploy)

```bash
# 0. One-shot prereqs
pip install oci-cli
oci setup bootstrap   # region: us-ashburn-1

# 1. Provision OCI infra (VCN, subnet, firewall, IP, VM)
./deploy/provision-oci.sh
# → prints public IP, saves to deploy/.vm-ip

# 2. Update DNS A-record: analytis.zyntra.company → <printed IP>

# 3. Prepare secrets
cp deploy/.env.prod.example deploy/.env.prod
$EDITOR deploy/.env.prod   # fill in POSTGRES_PASSWORD, API keys

# 4. First deploy (rsync + build + cert + migrate + smoke test)
./deploy/deploy.sh
```

## Subsequent updates

```bash
./deploy/deploy.sh   # same command — re-syncs, rebuilds, re-migrates
```

## Operations

```bash
# Tail logs
ssh ubuntu@$(cat deploy/.vm-ip) 'sudo docker compose -f /opt/analytis/deploy/docker-compose.prod.yml logs -f --tail=200'

# Manual backup
ssh ubuntu@$(cat deploy/.vm-ip) '/opt/analytis/deploy/backup/pg-backup.sh'

# Open SSH from a new IP (your IP changed)
oci network security-list update --security-list-id <SL_OCID> --force \
  --ingress-security-rules '[ ...new rule... ]'
```
