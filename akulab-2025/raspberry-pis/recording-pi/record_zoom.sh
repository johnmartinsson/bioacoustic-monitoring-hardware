#!/usr/bin/env bash

CONFIG_FILE="$(dirname "$0")/../config.ini"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Config file not found: $CONFIG_FILE"
  exit 1
fi

# Function to read a key from a given section
read_config() {
  local section="$1"
  local key="$2"
  awk -F= -v section="$section" -v key="$key" '
    $0 ~ "\\[" section "\\]" { in_section=1; next }
    in_section && $1 ~ key { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit }
    $0 ~ /^\[/ { in_section=0 }
  ' "$CONFIG_FILE"
}

# Read configuration values from [recordingpi]
LOCAL_RECORDING_DIR=$(read_config "recordingpi" "from_audio_dir")
SEGMENT_TIME=$(read_config "recordingpi" "segment_time")
SAMPLE_RATE=$(read_config "recordingpi" "sample_rate")

# Use defaults if needed
SEGMENT_TIME="${SEGMENT_TIME:-3600}"
SAMPLE_RATE="${SAMPLE_RATE:-48000}"

# Ensure the recording directory exists
mkdir -p "$LOCAL_RECORDING_DIR"

echo "Recording directory: $LOCAL_RECORDING_DIR"
echo "Segment time: ${SEGMENT_TIME}s"
echo "Sample rate: ${SAMPLE_RATE}Hz"

# Filename pattern
FILENAME_PATTERN="${LOCAL_RECORDING_DIR}/zoom_f8_pro_%Y%m%d_%H%M%S_%04d.wav"

# Start recording via arecord pipe into ffmpeg
arecord -D hw:2,0 \
        -f FLOAT_LE -c 8 -r "$SAMPLE_RATE" \
        -t raw \
    | ffmpeg -loglevel info \
        -f f32le -ar "$SAMPLE_RATE" -ac 8 -i pipe:0 \
        -c:a pcm_f32le \
        -f segment \
        -segment_time "$SEGMENT_TIME" \
        -segment_atclocktime 1 \
        -strftime 1 \
        -segment_format wav \
        -rf64 always \
        -reset_timestamps 1 \
        -write_bext 1 \
        -metadata creation_time="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
        -metadata coding_history="ZoomF8Pro USB ${SAMPLE_RATE}Hz/8ch float via arecord pipe" \
        "$FILENAME_PATTERN"

echo "Recording process started. Files will be segmented in ${SEGMENT_TIME} second chunks."
echo "Press Ctrl+C to stop recording."

