#!/usr/bin/env bash

CONFIG_FILE="$(dirname "$0")/../config.ini"
DRY_RUN=true

# Parse args
if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
fi

# Function to read a key from a given section in an INI file
read_config() {
  local section="$1"
  local key="$2"
  awk -F= -v section="$section" -v key="$key" '
    $0 ~ "\\[" section "\\]" { in_section=1; next }
    in_section && $1 ~ key { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/ { in_section=0 }
  ' "$CONFIG_FILE"
}

# Read values from config.ini
NAS_IP=$(read_config "nas" "nas_ip")
NAS_REMOTE_DIR=$(read_config "nas" "to_audio_dir")
LOCAL_MOUNT=$(read_config "analyticspi" "to_audio_dir")

# Create the local mount point
echo "Creating local mount point at $LOCAL_MOUNT..."
sudo mkdir -p "$LOCAL_MOUNT"

# Sanity check
if [[ "$NAS_IP" == "XXX" || "$NAS_REMOTE_DIR" == "XXX" ]]; then
  echo "❌ NAS config not fully defined in config.ini."
  exit 1
fi

# Check if already mounted
if mountpoint -q "$LOCAL_MOUNT"; then
  echo "ℹ️  Already mounted at $LOCAL_MOUNT — skipping."
  exit 0
fi

# Set ownership
echo "Setting ownership to analyticspi..."
sudo chown analyticspi:analyticspi "$LOCAL_MOUNT"

if $DRY_RUN; then
  echo "🧪 Dry run enabled: Skipping actual mount."
  exit 0
fi

# Mount the NAS via NFS
echo "Mounting NAS $NAS_IP:$NAS_REMOTE_DIR to $LOCAL_MOUNT..."
sudo mount -t nfs "${NAS_IP}:${NAS_REMOTE_DIR}" "$LOCAL_MOUNT"

# Confirm result
if mountpoint -q "$LOCAL_MOUNT"; then
  echo "✅ NAS mounted successfully at $LOCAL_MOUNT"
else
  echo "❌ Failed to mount NAS."
fi

