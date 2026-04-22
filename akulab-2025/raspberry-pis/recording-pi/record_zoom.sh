#!/usr/bin/env bash
#
# record_zoom.sh  –  Zoom F8 Pro 8‑ch float ⟶ FFmpeg segmenter
#

set -euo pipefail

# ───────────────────────── 1.  Wait for audio interface ─────────────────────────
echo "🔍 Waiting for Zoom F8 Pro (hw:2,0) to become available…"
while ! arecord -l | grep -q "card 2:.*F8"; do
  echo "❌ hw:2,0 not found. Retrying in 30 s…"
  sleep 30
done
echo "✅ Found Zoom F8 Pro."

# ───────────────────────── 2.  Read settings from config.ini ────────────────────
CONFIG_FILE="$(dirname "$0")/../config.ini"

read_config () {
  local section=$1 key=$2
  awk -F= -v s="\\[$section\\]" -v k="$key" '
    $0 ~ s          {inside=1; next}
    inside && $1 ~ k{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}
    /^\[/           {inside=0}
  ' "$CONFIG_FILE"
}

LOCAL_RECORDING_DIR=$(read_config recordingpi to_audio_dir)
SEGMENT_TIME=$(read_config recordingpi segment_time)
SAMPLE_RATE=$(read_config recordingpi sample_rate)

SEGMENT_TIME=${SEGMENT_TIME:-3600}
SAMPLE_RATE=${SAMPLE_RATE:-48000}

# ───────────────────────── 3.  Wait for USB‑HDD mount ───────────────────────────
USB_MOUNT_DIR=$(dirname "$(readlink -f "$LOCAL_RECORDING_DIR")")  # /home/…/usb_hdd
echo "🔍 Waiting for USB HDD mount at $USB_MOUNT_DIR …"

mount_ready () { mountpoint -q "$1"; }

until mount_ready "$USB_MOUNT_DIR"; do
  echo "❌ Drive not mounted yet. Retrying in 20 s…"
  sleep 20
done
echo "✅ USB HDD is mounted."

mkdir -p   "$LOCAL_RECORDING_DIR"
echo "Recording directory : $LOCAL_RECORDING_DIR"
echo "Segment time        : ${SEGMENT_TIME}s"
echo "Sample rate         : ${SAMPLE_RATE} Hz"

# ───────────────────────── 4.  Launch capture pipeline ──────────────────────────
FILENAME_PATTERN="${LOCAL_RECORDING_DIR}/auklab_%Y%m%dT%H%M%S.wav"
SEGMENT_LIST="${LOCAL_RECORDING_DIR}/zoom_manifest.csv"

export ALSA_PCM_DEBUG=0          # set to 1 if you want kernel ring‑buffer stats

arecord -D hw:2,0           \
        -f FLOAT_LE -c 8 -r "$SAMPLE_RATE" \
        -t raw              \
        -B 250000 -F 20000 -v |
ffmpeg  -loglevel info \
        -f f32le -ar "$SAMPLE_RATE" -ac 8 \
        -use_wallclock_as_timestamps 1 -i pipe:0 -copyts \
        -c:a pcm_f32le -rf64 always       \
        -f segment -segment_time "$SEGMENT_TIME" \
        -segment_atclocktime 1 -reset_timestamps 0 \
        -segment_format wav -strftime 1 \
        -segment_list "$SEGMENT_LIST" -segment_list_type csv \
        -avoid_negative_ts disabled \
        -write_bext 1        \
        -metadata coding_history="ZoomF8Pro USB ${SAMPLE_RATE}Hz/8ch float via arecord pipe" \
        -metadata comment="Ch1=BOND6; Ch2=FAR3; Ch3=TRI6; Ch4=TRI7C; Ch5=BOND1; Ch6=ROST2; Ch7=TRI2; Ch8=Bjorn1" \
        "$FILENAME_PATTERN"

echo "🎙  Recording started — files will roll every ${SEGMENT_TIME}s."
