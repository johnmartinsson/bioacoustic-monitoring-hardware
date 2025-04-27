#!/usr/bin/env bash

CONFIG_FILE="$(dirname "$0")/../config.ini"
DRY_RUN=false

if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
fi

read_config() {
  local section="$1"
  local key="$2"
  awk -F= -v section="$section" -v key="$key" '
    $0 ~ "\\[" section "\\]" { in_section=1; next }
    in_section && $1 ~ key { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/ { in_section=0 }
  ' "$CONFIG_FILE"
}

NAS_IP=$(read_config "nas" "nas_ip")
NAS_REMOTE_DIR=$(read_config "nas" "to_audio_dir")
LOCAL_MOUNT=$(read_config "analyticspi" "to_audio_dir")

echo "Creating local mount point at $LOCAL_MOUNT..."
mkdir -p "$LOCAL_MOUNT"
chown analyticspi:analyticspi "$LOCAL_MOUNT"

# Sanity check
if [[ "$NAS_IP" == "XXX" || "$NAS_REMOTE_DIR" == "XXX" ]]; then
  echo "❌ NAS config not fully defined in config.ini."
  exit 1
fi

if mountpoint -q "$LOCAL_MOUNT"; then
  echo "ℹ️  Already mounted at $LOCAL_MOUNT — skipping."
  exit 0
fi

if $DRY_RUN; then
  echo "🧪 Dry run enabled: Skipping actual mount."
  exit 0
fi

echo "Mounting NAS $NAS_IP:$NAS_REMOTE_DIR to $LOCAL_MOUNT..."
sudo mount -t nfs "${NAS_IP}:${NAS_REMOTE_DIR}" "$LOCAL_MOUNT"

if mountpoint -q "$LOCAL_MOUNT"; then
  echo "✅ NAS mounted successfully at $LOCAL_MOUNT"
else
  echo "❌ Failed to mount NAS."
fi

