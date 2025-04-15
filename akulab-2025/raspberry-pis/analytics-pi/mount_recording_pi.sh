#!/usr/bin/env bash

CONFIG_FILE="$(dirname "$0")/../config.ini"

# Retry config
MAX_RETRIES=30
RETRY_DELAY=30  # seconds

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
SSH_KEY="/home/analyticspi/.ssh/id_rsa"

# Already mounted?
if mountpoint -q "$LOCAL_MOUNT"; then
    echo "ℹ️  Already mounted at $LOCAL_MOUNT — skipping."
    exit 0
fi

# Create mount directory if needed
echo "📁 Creating local mount point at $LOCAL_MOUNT..."
mkdir -p "$LOCAL_MOUNT"
chown analyticspi:analyticspi "$LOCAL_MOUNT"

# Attempt to mount with retries
retry=0
while [ $retry -lt $MAX_RETRIES ]; do
    echo "🔁 Attempting to mount $REMOTE_USER@$REMOTE_IP:$REMOTE_DIR to $LOCAL_MOUNT (try $((retry+1))/$MAX_RETRIES)..."
    
    sshfs -o IdentityFile="$SSH_KEY",allow_other,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,uid=1000,gid=1000 \
        "$REMOTE_USER@$REMOTE_IP:$REMOTE_DIR" "$LOCAL_MOUNT"

    if mountpoint -q "$LOCAL_MOUNT"; then
        echo "✅ Successfully mounted at $LOCAL_MOUNT"
        exit 0
    else
        echo "❌ Mount failed. Will retry in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
        retry=$((retry + 1))
    fi
done

echo "🛑 Failed to mount after $MAX_RETRIES attempts."
exit 1

