#!/usr/bin/env bash
#
# Check that the USB HDD is still mounted.
# If it’s gone, try to remount it via mount_usb_hdd.sh
#

CONFIG_FILE="$(dirname "$0")/../config.ini"

# -------- utility to read keys from config.ini --------
read_config() {
  local section="$1" key="$2"
  awk -F= -v section="$section" -v key="$key" '
    $0 ~ "\\[" section "\\]" { in_section=1; next }
    in_section && $1 ~ key   { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/               { in_section=0 }
  ' "$CONFIG_FILE"
}

# --- paths from config.ini ---------------------------------------------------
TO_AUDIO_DIR=$(read_config "recordingpi" "to_audio_dir")   # e.g. /media/recordingpi/usb_hdd/audio_0422
USB_MOUNT_POINT="$(dirname "$TO_AUDIO_DIR")"               # => /media/recordingpi/usb_hdd

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/home/recordingpi/logs/mount_watchdog"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/$(date +%F)_mount_watchdog.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"; }

# ---------------------------------------------------------------------------
if mountpoint -q "$USB_MOUNT_POINT"; then
  log "✅ USB HDD mount OK: $USB_MOUNT_POINT"
else
  log "❌ USB HDD not mounted. Attempting remount…"
  #"$SCRIPT_DIR/mount_usb_hdd.sh"
fi
