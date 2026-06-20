#!/usr/bin/env bash
# Provisions OCI infra for analytis: VCN, IGW, route table, subnet, security list,
# reserved public IP, and an Ampere A1 Flex VM with cloud-init.yaml baked in.
#
# Prereqs (one-shot, see docs/deploy-oracle-cloud.md §8.1):
#   - oci-cli installed and `oci setup bootstrap` completed
#   - SSH keypair at ~/.ssh/id_ed25519 (or change SSH_PUBLIC_KEY below)
#
# Usage:
#   ./deploy/provision-oci.sh
#
# Outputs: public IP + ready-to-paste ssh command. Save the IP in deploy/.vm-ip.

set -euo pipefail

# ============================================================
# Tunables
# ============================================================
REGION="sa-saopaulo-1"                # only region available in this Free Tier
AD_INDICES=(1)                        # sa-saopaulo-1 has a single AD
DISPLAY_NAME="analytis-prod"
VCN_CIDR="10.0.0.0/16"
SUBNET_CIDR="10.0.1.0/24"
SHAPE="VM.Standard.E2.1.Micro"        # AMD x86, 1 OCPU / 1 GB — near-guaranteed capacity
LAUNCH_RETRY_LIMIT=5                  # E2.Micro should succeed first try
LAUNCH_RETRY_DELAY=20
BOOT_VOL_GB=100
OS_NAME="Canonical Ubuntu"
OS_VERSION="22.04"
SSH_PUBLIC_KEY="${HOME}/.ssh/id_ed25519.pub"
ALLOWED_SSH_CIDR="189.113.224.46/32"
CLOUD_INIT_FILE="$(dirname "$0")/cloud-init.yaml"
OCI_CONFIG="${OCI_CLI_CONFIG_FILE:-${HOME}/.oci/config}"

# ============================================================
# Helpers
# ============================================================
log() { printf "\033[1;34m[provision]\033[0m %s\n" "$*"; }
die() { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

# Auto-detect oci binary (PATH first, then the Windows venv we created)
OCI="${OCI_CLI:-oci}"
if ! command -v "$OCI" >/dev/null 2>&1; then
  if [[ -x "/c/oci-cli-venv/Scripts/oci.exe" ]]; then
    OCI="/c/oci-cli-venv/Scripts/oci.exe"
  else
    die "oci-cli not found. Install: pip install oci-cli && oci setup bootstrap"
  fi
fi

[[ -f "$SSH_PUBLIC_KEY" ]] || die "SSH public key not found at $SSH_PUBLIC_KEY"
[[ -f "$CLOUD_INIT_FILE" ]] || die "cloud-init.yaml not found at $CLOUD_INIT_FILE"
[[ -f "$OCI_CONFIG" ]] || die "OCI config not found at $OCI_CONFIG. Run 'oci setup bootstrap' first."

# Force every oci call to hit $REGION regardless of config default
export OCI_CLI_REGION="$REGION"

# ============================================================
# Resolve compartment + tenancy + AD + image
# ============================================================
log "Reading tenancy OCID from $OCI_CONFIG..."
TENANCY_OCID="$(grep -E "^tenancy=" "$OCI_CONFIG" | head -n1 | cut -d= -f2 | tr -d '\r')"
[[ -n "$TENANCY_OCID" ]] || die "tenancy= line missing in $OCI_CONFIG"
COMPARTMENT_OCID="$TENANCY_OCID"      # use root compartment
log "Tenancy OCID: ${TENANCY_OCID:0:30}..."

log "Listing availability domains in $REGION..."
mapfile -t AD_NAMES < <("$OCI" iam availability-domain list --compartment-id "$COMPARTMENT_OCID" \
  --query 'data[].name' --raw-output 2>/dev/null | tr -d '[]" ,' | grep -v '^$')
[[ ${#AD_NAMES[@]} -gt 0 ]] || die "No ADs returned"
log "Found ${#AD_NAMES[@]} AD(s): ${AD_NAMES[*]}"

log "Resolving latest ${OS_NAME} ${OS_VERSION} ARM image..."
IMAGE_OCID="$("$OCI" compute image list --compartment-id "$COMPARTMENT_OCID" \
  --operating-system "$OS_NAME" --operating-system-version "$OS_VERSION" \
  --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC --limit 1 \
  --query 'data[0].id' --raw-output)"
[[ -n "$IMAGE_OCID" && "$IMAGE_OCID" != "null" ]] || die "No matching image found"
log "Image OCID: ${IMAGE_OCID:0:30}..."

# ============================================================
# VCN + IGW + route table + subnet (idempotent — reuse on retry)
# ============================================================
log "Checking for existing VCN '${DISPLAY_NAME}-vcn'..."
VCN_OCID="$("$OCI" network vcn list --compartment-id "$COMPARTMENT_OCID" \
  --display-name "${DISPLAY_NAME}-vcn" --lifecycle-state AVAILABLE \
  --query 'data[0].id' --raw-output 2>/dev/null || true)"

if [[ -n "$VCN_OCID" && "$VCN_OCID" != "null" ]]; then
  log "Reusing existing VCN: ${VCN_OCID:0:30}..."
else
  log "Creating VCN..."
  VCN_OCID="$("$OCI" network vcn create --compartment-id "$COMPARTMENT_OCID" \
    --cidr-block "$VCN_CIDR" --display-name "${DISPLAY_NAME}-vcn" \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
  log "VCN: ${VCN_OCID:0:30}..."
fi

IGW_OCID="$("$OCI" network internet-gateway list --compartment-id "$COMPARTMENT_OCID" \
  --vcn-id "$VCN_OCID" --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [[ -z "$IGW_OCID" || "$IGW_OCID" == "null" ]]; then
  log "Creating Internet Gateway..."
  IGW_OCID="$("$OCI" network internet-gateway create --compartment-id "$COMPARTMENT_OCID" \
    --vcn-id "$VCN_OCID" --display-name "${DISPLAY_NAME}-igw" --is-enabled true \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
else
  log "Reusing IGW: ${IGW_OCID:0:30}..."
fi

log "Ensuring default route table has 0.0.0.0/0 → IGW..."
RT_OCID="$("$OCI" network vcn get --vcn-id "$VCN_OCID" \
  --query 'data."default-route-table-id"' --raw-output)"
"$OCI" network route-table update --rt-id "$RT_OCID" --force \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW_OCID\"}]" \
  --wait-for-state AVAILABLE >/dev/null 2>&1 || true

SL_OCID="$("$OCI" network security-list list --compartment-id "$COMPARTMENT_OCID" \
  --vcn-id "$VCN_OCID" --display-name "${DISPLAY_NAME}-sl" \
  --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [[ -z "$SL_OCID" || "$SL_OCID" == "null" ]]; then
  log "Creating security list..."
  SL_RULES_INGRESS=$(cat <<EOF
[
  {"protocol":"6","source":"$ALLOWED_SSH_CIDR","sourceType":"CIDR_BLOCK","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
  {"protocol":"6","source":"0.0.0.0/0","sourceType":"CIDR_BLOCK","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
  {"protocol":"6","source":"0.0.0.0/0","sourceType":"CIDR_BLOCK","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":443,"max":443}}}
]
EOF
)
  SL_RULES_EGRESS='[{"destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","protocol":"all","isStateless":false}]'
  SL_OCID="$("$OCI" network security-list create --compartment-id "$COMPARTMENT_OCID" \
    --vcn-id "$VCN_OCID" --display-name "${DISPLAY_NAME}-sl" \
    --ingress-security-rules "$SL_RULES_INGRESS" \
    --egress-security-rules "$SL_RULES_EGRESS" \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
else
  log "Reusing security list: ${SL_OCID:0:30}..."
fi

SUBNET_OCID="$("$OCI" network subnet list --compartment-id "$COMPARTMENT_OCID" \
  --vcn-id "$VCN_OCID" --display-name "${DISPLAY_NAME}-subnet" \
  --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [[ -n "$SUBNET_OCID" && "$SUBNET_OCID" != "null" ]]; then
  log "Reusing subnet: ${SUBNET_OCID:0:30}..."
else
  log "Creating public subnet..."
  SUBNET_OCID="$("$OCI" network subnet create --compartment-id "$COMPARTMENT_OCID" \
    --vcn-id "$VCN_OCID" --cidr-block "$SUBNET_CIDR" \
    --display-name "${DISPLAY_NAME}-subnet" \
    --route-table-id "$RT_OCID" \
    --security-list-ids "[\"$SL_OCID\"]" \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
fi

# ============================================================
# Instance launch — retry on capacity (most common SP failure)
# ============================================================
log "Launching $SHAPE — up to $LAUNCH_RETRY_LIMIT attempts @ ${LAUNCH_RETRY_DELAY}s"

INSTANCE_OCID=""
LAUNCH_ERR=""
attempt=0
while [[ $attempt -lt $LAUNCH_RETRY_LIMIT ]]; do
  attempt=$((attempt + 1))
  for idx in "${AD_INDICES[@]}"; do
    pos=$((idx - 1))
    [[ $pos -lt ${#AD_NAMES[@]} ]] || continue
    AD_NAME="${AD_NAMES[$pos]}"
    log "  [attempt $attempt/$LAUNCH_RETRY_LIMIT] AD $idx ($AD_NAME)..."
    if LAUNCH_OUT=$("$OCI" compute instance launch \
        --compartment-id "$COMPARTMENT_OCID" \
        --availability-domain "$AD_NAME" \
        --shape "$SHAPE" \
        --image-id "$IMAGE_OCID" \
        --subnet-id "$SUBNET_OCID" \
        --display-name "$DISPLAY_NAME" \
        --assign-public-ip true \
        --ssh-authorized-keys-file "$SSH_PUBLIC_KEY" \
        --user-data-file "$CLOUD_INIT_FILE" \
        --boot-volume-size-in-gbs "$BOOT_VOL_GB" \
        --wait-for-state RUNNING \
        --query 'data.id' --raw-output 2>&1); then
    # --wait-for-state emits "Action completed. Waiting until..." to stderr,
    # which 2>&1 merged with the OCID — extract just the OCID (last token).
    INSTANCE_OCID=$(echo "$LAUNCH_OUT" | grep -oE 'ocid1\.instance\.[^[:space:]]+' | tail -n1)
    log "  ✓ Launched in AD $idx"
    break
  else
    LAUNCH_ERR="$LAUNCH_OUT"
    if echo "$LAUNCH_OUT" | grep -qi "out of host capacity\|outofcapacity"; then
      log "  ✗ AD $idx: out of capacity — trying next"
    else
      log "  ✗ AD $idx failed (non-capacity):"
      echo "$LAUNCH_OUT" | head -5
      die "Non-capacity launch error — aborting"
    fi
  fi
  done   # for AD
  [[ -n "$INSTANCE_OCID" ]] && break   # success → exit retry loop
  log "  No capacity this round. Sleeping ${LAUNCH_RETRY_DELAY}s before retry..."
  sleep "$LAUNCH_RETRY_DELAY"
done   # while retry

[[ -n "$INSTANCE_OCID" ]] || die "Capacity unavailable after $LAUNCH_RETRY_LIMIT attempts (~$((LAUNCH_RETRY_LIMIT * LAUNCH_RETRY_DELAY / 60)) min). Try again later or upgrade to PAYG. Last error: $LAUNCH_ERR"

log "Resolving public IP..."
sleep 5
PUBLIC_IP="$("$OCI" compute instance list-vnics --instance-id "$INSTANCE_OCID" \
  --query 'data[0]."public-ip"' --raw-output)"

echo "$PUBLIC_IP" > "$(dirname "$0")/.vm-ip"

cat <<EOF

╔══════════════════════════════════════════════════════════════╗
║  VM READY                                                    ║
╠══════════════════════════════════════════════════════════════╣
║  Public IP:  $PUBLIC_IP
║  Saved to:   deploy/.vm-ip
║
║  Next steps:
║    1. Point DNS A-record:  analytis.zyntra.company → $PUBLIC_IP
║    2. Wait for cloud-init  (~3 min):
║         ssh ubuntu@$PUBLIC_IP 'test -f /opt/analytis/.cloud-init-done'
║    3. Configure secrets:
║         cp deploy/.env.prod.example deploy/.env.prod
║         # edit deploy/.env.prod with real values
║    4. First deploy:
║         ./deploy/deploy.sh
╚══════════════════════════════════════════════════════════════╝
EOF
