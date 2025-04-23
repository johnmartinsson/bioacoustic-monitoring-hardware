#!/usr/bin/env bash
#
# Lightweight helper – just (re)run the normal fstab mount.
# Keeps all options (noatime,commit=30,errors=remount-ro,nofail,…) in /etc/fstab
#

CONFIG_FILE="$(dirname "$0")/../config.ini"
read_config() {
  local s="$1" k="$2"
  awk -F= -v s="$s" -v k="$k" '
    $0 ~ "\\[" s "\\]" { in=1; next }
    in && $1 ~ k       { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/         { in=0 }
  ' "$CONFIG_FILE"
}

TO_AUDIO_DIR=$(read_config "recordingpi" "to_audio_dir")
USB_MOUNT_POINT="$(dirname "$TO_AUDIO_DIR")"

echo "🔁 Mounting USB HDD at $USB_MOUNT_POINT…"
mount "$USB_MOUNT_POINT"

if mountpoint -q "$USB_MOUNT_POINT"; then
  echo "✅ Mounted successfully."
else
  echo "❌ Mount failed – check /var/log/syslog."
fi
