#!/usr/bin/env bash
#
# test_teardown.sh – Tear down the local test environment created by test_setup.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_BASE=/tmp/akulab_test
AWK_PREV_FILE="$TEST_BASE/awk_previous_target"

USB_HDD="$TEST_BASE/usb_hdd"
RPI_MOUNT="$TEST_BASE/rpi_mount"
NAS_MOUNT="$TEST_BASE/nas"

echo "=== Unmounting bind mounts (requires sudo) ==="
unmount_if_mounted() {
  if mountpoint -q "$1" 2>/dev/null; then
    sudo umount "$1" && echo "  Unmounted $1"
  else
    echo "  Not mounted, skipping: $1"
  fi
}

# RPI_MOUNT is bound from AUDIO_DIR (inside USB_HDD), so unmount it first
unmount_if_mounted "$RPI_MOUNT"
unmount_if_mounted "$USB_HDD"
unmount_if_mounted "$NAS_MOUNT"

echo "=== Restoring awk alternative (if changed by setup) ==="
if [[ -f "$AWK_PREV_FILE" ]] && command -v update-alternatives >/dev/null 2>&1; then
  PREV_AWK_TARGET=$(cat "$AWK_PREV_FILE")
  if [[ -n "$PREV_AWK_TARGET" ]]; then
    sudo update-alternatives --set awk "$PREV_AWK_TARGET" >/dev/null || true
    echo "  awk restored to: $(readlink -f "$(command -v awk)")"
  fi
else
  echo "  No awk restore needed."
fi

echo "=== Removing test directories ==="
rm -rf "$TEST_BASE"

echo "=== Restoring original config.ini ==="
CONFIG="$SCRIPT_DIR/config.ini"
if [[ -f "${CONFIG}.bak" ]]; then
  mv "${CONFIG}.bak" "$CONFIG"
  echo "  Restored config.ini from backup."
else
  echo "  No backup found (${CONFIG}.bak missing), skipping restore."
fi

echo "=== Teardown complete ==="
