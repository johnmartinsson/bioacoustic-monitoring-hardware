#!/usr/bin/env bash
#
# record_zoom_hourly.sh
#
# 1) Wait until the specified top-of-minute or top-of-hour with millisecond accuracy
# 2) Start a single ffmpeg process that streams audio from the Zoom F8 Pro as a USB interface
# 3) Segment the audio into chunks of the specified duration.
#

CONFIG_FILE="$(dirname "$0")/config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE"
  exit 1
fi

# Function to read configuration parameters with defaults
read_config() {
  local key=$1
  local default_value=$2
  local value=$(awk -F= -v key="$key" '$1 ~ key {print $2}' "$CONFIG_FILE" | tr -d '[:space:]' | tr -d "'")
  echo "${value:-$default_value}"
}

# Read configuration parameters
LOCAL_RECORDING_DIR=$(read_config "local_recording_dir" "./zoom_recordings")
SEGMENT_TIME=$(read_config "segment_time" "3600")  # Default to 3600 seconds (1 hour)
SAMPLE_RATE=$(read_config "sample_rate" "48000")         # Default to 48000 Hz

# Create the recording directory if it doesn't exist
mkdir -p "$LOCAL_RECORDING_DIR"

echo "Recording directory: $LOCAL_RECORDING_DIR"
echo "Recording duration: $SEGMENT_TIME seconds"

# Filenames: e.g., zoom_audio_20250328_130000_0001.wav
FILENAME_PATTERN="${LOCAL_RECORDING_DIR}/zoom_f8_pro_%Y%m%d_%H%M%S_%04d.wav"

#!/usr/bin/env bash

# Example "improved" ffmpeg command for hour-aligned, 8‑channel, 48 kHz float WAV segments:

arecord -D hw:2,0 \
        -f FLOAT_LE -c 8 -r 48000 \
        -t raw \
    | ffmpeg -loglevel info \
        -f f32le -ar 48000 -ac 8 -i pipe:0 \
        -c:a pcm_f32le \
        -f segment \
        -segment_time "${SEGMENT_TIME}" \
        -segment_atclocktime 1 \
        -strftime 1 \
        -segment_format wav \
        -rf64 always \
        -reset_timestamps 1 \
        -write_bext 1 \
        -metadata creation_time="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
        -metadata coding_history="ZoomF8Pro USB 48000Hz/8ch float via arecord pipe" \
	"${FILENAME_PATTERN}"

echo "Recording process started. Files will be segmented in ${SEGMENT_TIME} second chunks."
echo "Press Ctrl+C to stop recording."
