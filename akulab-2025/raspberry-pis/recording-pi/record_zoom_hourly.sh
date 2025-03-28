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
RECORD_DURATION=$(read_config "record_duration" "3600")  # Default to 3600 seconds (1 hour)
SAMPLE_RATE=$(read_config "sample_rate" "48000")         # Default to 48000 Hz
CHANNELS=$(read_config "channels" "8")                  # Default to 8 channels
WAIT_UNTIL=$(read_config "wait_until" "minute")         # Default to 'minute'

# Create the recording directory if it doesn't exist
mkdir -p "$LOCAL_RECORDING_DIR"

echo "Recording directory: $LOCAL_RECORDING_DIR"
echo "Recording duration: $RECORD_DURATION seconds"
echo "Sample rate: $SAMPLE_RATE Hz"
echo "Channels: $CHANNELS"
echo "Wait until: $WAIT_UNTIL"

# Filenames: e.g., zoom_audio_20250328_130000_0001.wav
FILENAME_PATTERN="${LOCAL_RECORDING_DIR}/zoom_audio_%Y%m%d_%H%M%S_%04d.wav"

# Wait until top-of-hour with millisecond accuracy
wait_until_top_of_hour_ms() {
  now_ms=$(date +%s%3N)
  ms_into_hour=$((now_ms % 3600000))
  ms_left=$((3600000 - ms_into_hour))
  if [ $ms_left -eq 3600000 ]; then
    ms_left=0
  fi
  sec_float=$(awk -v val="$ms_left" 'BEGIN {printf "%.3f", val/1000.0}')
  echo "Current time: $(date +%T.%3N). Sleeping $sec_float seconds to top-of-hour..."
  sleep "$sec_float"
}

# Wait until top-of-minute with millisecond accuracy
wait_until_top_of_minute_ms() {
  now_ms=$(date +%s%3N)   # e.g., 1698742412345 (ms)
  ms_into_minute=$((now_ms % 60000))
  ms_left=$((60000 - ms_into_minute))
  if [ "$ms_left" -eq 60000 ]; then
    ms_left=0  # already exactly HH:MM:00.000
  fi
  sec_float=$(awk -v val="$ms_left" 'BEGIN {printf "%.3f", val/1000.0}')
  echo "Current time: $(date +%T.%3N). Sleeping $sec_float second(s) to next full minute..."
  sleep "$sec_float"
}

# Determine which wait method to use
if [ "$WAIT_UNTIL" == "hour" ]; then
  echo "Waiting for next top-of-hour with ms accuracy..."
  wait_until_top_of_hour_ms
elif [ "$WAIT_UNTIL" == "minute" ]; then
  echo "Waiting for next top-of-minute with ms accuracy..."
  wait_until_top_of_minute_ms
elif [ "$WAIT_UNTIL" == "none" ]; then
  echo "Skipping wait_until. Starting recording immediately."
else
  echo "Invalid wait_until value in config.ini: $WAIT_UNTIL. Using default 'minute'."
  wait_until_top_of_minute_ms
fi

echo "Reached specified time boundary. Launching ffmpeg..."

# Record from Zoom F8 Pro
ffmpeg -loglevel info \
    -f alsa \
    -channels "$CHANNELS" \
    -sample_rate "$SAMPLE_RATE" \
    -acodec pcm_f32le \
    -i "hw:2,0" \
    -f segment \
    -segment_time "$RECORD_DURATION" \
    -segment_format wav \
    -segment_atclocktime 0 \
    -strftime 1 \
    -reset_timestamps 1 \
    -write_bext 1 \
    -rf64 always \
    -metadata creation_time="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
    -metadata coding_history="ZoomF8Pro USB ${SAMPLE_RATE}Hz/${CHANNELS}ch float" \
    "$FILENAME_PATTERN"

echo "Recording process started. Files will be segmented in ${RECORD_DURATION} second chunks."
echo "Press Ctrl+C to stop recording."