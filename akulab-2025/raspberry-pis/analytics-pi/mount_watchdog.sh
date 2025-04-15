#!/usr/bin/env bash

CONFIG_FILE="$(dirname "$0")/../config.ini"

# Read value from config.ini
read_config() {
  local section="$1"
  local key="$2"
  awk -F= -v section="$section" -v key="$key" '
    $0 ~ "\\[" section "\\]" { in_section=1; next }
    in_section && $1 ~ key { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/ { in_section=0 }
  ' "$CONFIG_FILE"
}

# Get local mount paths from config.ini
RECORDINGPI_MOUNT=$(read_config "analyticspi" "from_audio_dir")
NAS_MOUNT=$(read_config "analyticspi" "to_audio_dir")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/home/analyticspi/mount_watchdog.log"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check and remount Recording Pi
if mountpoint -q "$RECORDINGPI_MOUNT"; then
  log "✅ Recording Pi mount OK: $RECORDINGPI_MOUNT"
else
  log "❌ Recording Pi mount missing. Attempting to remount..."
  "$SCRIPT_DIR/mount_recording_pi.sh"
fi

# Check and remount NAS
if mountpoint -q "$NAS_MOUNT"; then
  log "✅ NAS mount OK: $NAS_MOUNT"
else
  log "❌ NAS mount missing. Attempting to remount..."
  "$SCRIPT_DIR/mount_nas.sh"
fi

