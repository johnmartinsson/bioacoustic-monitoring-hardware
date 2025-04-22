#!/usr/bin/env bash
#
# pool_logs.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.ini"

# Function to read a value from a given [section] and key in config.ini
read_config() {
  local section="$1"
  local key="$2"
  awk -F= -v sctn="$section" -v ky="$key" '
    $0 ~ "\\[" sctn "\\]" { in_section=1; next }
    in_section && $1 ~ ky {
      val=$2
      gsub(/^[ \t]+|[ \t]+$/, "", val)  # strip whitespace
      print val
      exit
    }
    $0 ~ /^\[/ { in_section=0 }
  ' "$CONFIG_FILE"
}

########################################
# 1) Read configuration
########################################
CLOCKPI_IP=$(read_config "clockpi" "clockpi_ip")
CLOCKPI_USER=$(read_config "clockpi" "clockpi_user")

RECORDINGPI_IP=$(read_config "recordingpi" "recordingpi_ip")
RECORDINGPI_USER=$(read_config "recordingpi" "recordingpi_user")

ANALYTICSPI_USER=$(read_config "analyticspi" "analyticspi_user")
# (ANALYTICSPI_IP is unused if we're doing local copies.)

########################################
# 2) Define local target directories
########################################
BASE_POOLED_DIR="/home/${ANALYTICSPI_USER}/logs/pooled"
CLOCKPI_TARGET="${BASE_POOLED_DIR}/clockpi"
RECORDINGPI_TARGET="${BASE_POOLED_DIR}/recordingpi"
ANALYTICSPI_TARGET="${BASE_POOLED_DIR}/analyticspi"

mkdir -p "$CLOCKPI_TARGET" "$RECORDINGPI_TARGET" "$ANALYTICSPI_TARGET"

########################################
# 3) RSYNC from Clock Pi
########################################
echo "=== Syncing logs from Clock Pi (${CLOCKPI_IP}) ==="
rsync -avz \
  --exclude="*.gz" \
  "${CLOCKPI_USER}@${CLOCKPI_IP}:/home/${CLOCKPI_USER}/logs/" \
  "$CLOCKPI_TARGET/"

########################################
# 4) RSYNC from Recording Pi
########################################
echo "=== Syncing logs from Recording Pi (${RECORDINGPI_IP}) ==="
rsync -avz \
  --exclude="*.gz" \
  "${RECORDINGPI_USER}@${RECORDINGPI_IP}:/home/${RECORDINGPI_USER}/logs/" \
  "$RECORDINGPI_TARGET/"

########################################
# 5) Copy local logs from Analytics Pi
########################################
# --exclude="pooled" prevents copying the pooled/ folder into itself
echo "=== Copying local logs from Analytics Pi ==="
rsync -av \
  --exclude="*.gz" \
  --exclude="pooled" \
  "/home/${ANALYTICSPI_USER}/logs/" \
  "$ANALYTICSPI_TARGET/"

echo "All logs have been pooled into $BASE_POOLED_DIR."

