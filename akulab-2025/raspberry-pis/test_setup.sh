#!/usr/bin/env bash
#
# test_setup.sh – Set up a local test environment for record_zoom_f3.sh + backup_recordings.py
#
# Creates fake mounts under /tmp/akulab_test and a test config.ini
# (original is backed up).
#
# Usage:
#   ./test_setup.sh          # set up
#   ./test_teardown.sh       # clean up when done
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_BASE=/tmp/akulab_test
AWK_PREV_FILE="$TEST_BASE/awk_previous_target"

# Directories that mirror the real layout
USB_HDD="$TEST_BASE/usb_hdd"                  # mountpoint  → simulates USB HDD
AUDIO_DIR="$USB_HDD/Audio"                    # to_audio_dir for record_zoom_f3.sh
RPI_MOUNT="$TEST_BASE/rpi_mount"              # mountpoint  → simulates SSHFS from recording-pi
NAS_MOUNT="$TEST_BASE/nas"                    # mountpoint  → simulates NFS NAS
echo "=== Creating test directories ==="
mkdir -p "$AUDIO_DIR" "$RPI_MOUNT" "$NAS_MOUNT"

# ── Bind mounts ───────────────────────────────────────────────────────────────
# mount --bind on itself turns any plain dir into a real mountpoint.
echo "=== Creating bind mounts (requires sudo) ==="

already_mounted() { mountpoint -q "$1" 2>/dev/null; }

already_mounted "$USB_HDD"   || sudo mount --bind "$USB_HDD"   "$USB_HDD"
already_mounted "$RPI_MOUNT" || sudo mount --bind "$AUDIO_DIR" "$RPI_MOUNT"
already_mounted "$NAS_MOUNT" || sudo mount --bind "$NAS_MOUNT" "$NAS_MOUNT"

echo "  USB_HDD   → $USB_HDD   (mountpoint: $(mountpoint "$USB_HDD"))"
echo "  RPI_MOUNT → $RPI_MOUNT (mountpoint: $(mountpoint "$RPI_MOUNT"))"
echo "  NAS_MOUNT → $NAS_MOUNT (mountpoint: $(mountpoint "$NAS_MOUNT"))"

echo "=== Ensuring awk compatibility for existing record parser ==="
if command -v mawk >/dev/null 2>&1 && command -v update-alternatives >/dev/null 2>&1; then
	CURRENT_AWK_TARGET=$(readlink -f "$(command -v awk)" || true)
	MAWK_TARGET=$(readlink -f "$(command -v mawk)" || true)

	if [[ -n "$CURRENT_AWK_TARGET" && -n "$MAWK_TARGET" ]]; then
		echo "$CURRENT_AWK_TARGET" > "$AWK_PREV_FILE"
		if [[ "$CURRENT_AWK_TARGET" != "$MAWK_TARGET" ]]; then
			sudo update-alternatives --set awk "$MAWK_TARGET" >/dev/null
			echo "  Switched awk to mawk for this test run."
		else
			echo "  awk already points to mawk."
		fi
		echo "  awk now resolves to: $(readlink -f "$(command -v awk)")"
	fi
else
	echo "  WARNING: mawk or update-alternatives not available; parser may still fail with current awk."
fi

# ── Test config.ini ───────────────────────────────────────────────────────────
echo "=== Writing test config.ini (original backed up as config.ini.bak) ==="
CONFIG="$SCRIPT_DIR/config.ini"
cp --update=none "$CONFIG" "${CONFIG}.bak"

cat > "$CONFIG" << CONF
[clockpi]
clockpi_ip = 192.168.1.64
clockpi_user = clockpi

[nas]
nas_ip = 192.168.1.65
nas_user = john
to_audio_dir = /volume1/BSP_data/Audio

[analyticspi]
analyticspi_ip = 192.168.1.155
analyticspi_user = analyticspi
from_audio_dir = ${RPI_MOUNT}
to_audio_dir   = ${NAS_MOUNT}
verify_sha256  = false

[recordingpi]
recordingpi_ip = 192.168.1.79
recordingpi_user = recordingpi
to_audio_dir = ${AUDIO_DIR}
segment_time = 10
sample_rate  = 48000
CONF

# Sanity-check using the exact awk expression used by record scripts.
# If this fails here, record_zoom_f3.sh will see an empty LOCAL_RECORDING_DIR.
PARSED_TO_AUDIO_DIR=$(awk -F= -v s='\\[recordingpi\\]' -v k='to_audio_dir' '
	$0 ~ s          {inside=1; next}
	inside && $1 ~ k{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}
	/^\[/           {inside=0}
' "$CONFIG" 2>/dev/null || true)

if [[ -z "$PARSED_TO_AUDIO_DIR" ]]; then
	cat > "$CONFIG" << CONF_FALLBACK
[clockpi]
clockpi_ip=192.168.1.64
clockpi_user=clockpi

[nas]
nas_ip=192.168.1.65
nas_user=john
to_audio_dir=/volume1/BSP_data/Audio

[analyticspi]
analyticspi_ip=192.168.1.155
analyticspi_user=analyticspi
from_audio_dir=${RPI_MOUNT}
to_audio_dir=${NAS_MOUNT}
verify_sha256=false

[recordingpi]
recordingpi_ip=192.168.1.79
recordingpi_user=recordingpi
to_audio_dir=${AUDIO_DIR}
segment_time=10
sample_rate=48000
CONF_FALLBACK

	PARSED_TO_AUDIO_DIR=$(awk -F= -v s='\\[recordingpi\\]' -v k='to_audio_dir' '
		$0 ~ s          {inside=1; next}
		inside && $1 ~ k{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}
		/^\[/           {inside=0}
	' "$CONFIG" 2>/dev/null || true)
fi

if [[ -z "$PARSED_TO_AUDIO_DIR" ]]; then
	echo "ERROR: test_setup could not generate a config.ini format parseable by the existing record script awk parser." >&2
	echo "Please run: awk --version (or mawk -W version) and share output." >&2
	exit 1
fi

PARSED_USB_MOUNT_DIR=$(dirname "$(readlink -f "$PARSED_TO_AUDIO_DIR")")
echo "Parser sanity-check: recordingpi.to_audio_dir = $PARSED_TO_AUDIO_DIR"
echo "Parser sanity-check: USB mount dir         = $PARSED_USB_MOUNT_DIR"
if ! mountpoint -q "$PARSED_USB_MOUNT_DIR"; then
	echo "ERROR: Parsed USB mount dir is not a mountpoint: $PARSED_USB_MOUNT_DIR" >&2
	exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Test environment ready. Run in separate terminals:             ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                  ║"
echo "║  Terminal 1 – start recording (Ctrl-C after ~30 s):             ║"
echo "║    ./recording-pi/record_zoom_f3.sh                              ║"
echo "║                                                                  ║"
echo "║  Terminal 2 – run backup (after a few segments appear):         ║"
echo "║    python3 backup_recordings.py --rpi analyticspi               ║"
echo "║                                                                  ║"
echo "║  Inspect results:                                                ║"
echo "║    ls -lh $AUDIO_DIR/                    ║"
echo "║    cat    $AUDIO_DIR/zoom_manifest.csv   ║"
echo "║    ls -lh $NAS_MOUNT/                    ║"
echo "║    cat    $NAS_MOUNT/zoom_manifest.csv   ║"
echo "║                                                                  ║"
echo "║  When done:  ./test_teardown.sh                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
