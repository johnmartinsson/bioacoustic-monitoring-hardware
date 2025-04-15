#!/usr/bin/env bash

CONFIG_FILE="$(dirname "$0")/../config.ini"

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
REMOTE_USER=$(read_config "recordingpi" "recordingpi_user")
REMOTE_IP=$(read_config "recordingpi" "recordingpi_ip")
REMOTE_DIR=$(read_config "recordingpi" "from_audio_dir")

LOCAL_MOUNT=$(read_config "analyticspi" "from_audio_dir")
SSH_KEY="/home/analyticspi/.ssh/id_rsa"  # assuming analyticspi always runs this

# Check if already mounted
if mountpoint -q "$LOCAL_MOUNT"; then
    echo "ℹ️  Already mounted at $LOCAL_MOUNT — skipping."
    exit 0
fi

# Create the mount directory if it doesn't exist
echo "Creating local mount point at $LOCAL_MOUNT..."
sudo mkdir -p "$LOCAL_MOUNT"

# Set ownership to analyticspi
echo "Setting ownership to analyticspi..."
sudo chown analyticspi:analyticspi "$LOCAL_MOUNT"

# Perform the mount using sshfs
echo "Mounting $REMOTE_USER@$REMOTE_IP:$REMOTE_DIR to $LOCAL_MOUNT..."
sshfs -o IdentityFile="$SSH_KEY",allow_other,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,uid=1000,gid=1000 "$REMOTE_USER@$REMOTE_IP:$REMOTE_DIR" "$LOCAL_MOUNT"

# Confirm result
if mountpoint -q "$LOCAL_MOUNT"; then
    echo "✅ Mounted successfully at $LOCAL_MOUNT"
else
    echo "❌ Failed to mount."
fi

