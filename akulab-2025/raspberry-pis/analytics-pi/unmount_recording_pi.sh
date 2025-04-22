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

# Read the local mount path from the analyticspi section
LOCAL_MOUNT=$(read_config "analyticspi" "from_audio_dir")

echo "Attempting to unmount $LOCAL_MOUNT..."

# Only try if it's actually mounted
if mountpoint -q "$LOCAL_MOUNT"; then
  fusermount -u "$LOCAL_MOUNT"
  if [ $? -eq 0 ]; then
    echo "✅ Successfully unmounted $LOCAL_MOUNT"
  else
    echo "❌ Failed to unmount $LOCAL_MOUNT"
  fi
else
  echo "ℹ️  $LOCAL_MOUNT is not currently mounted"
fi

