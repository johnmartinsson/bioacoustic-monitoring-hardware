#!/usr/bin/env bash
#
# record_zoom_hourly.sh
#
# 1) Wait until top-of-hour with millisecond accuracy
# 2) Start a single ffmpeg process that streams 8-channel float audio
#    from the Zoom F8 Pro as a USB interface
# 3) Segment the audio in 1-hour chunks, each chunk exactly one hour long.
#

CONFIG_FILE="$(dirname "$0")/../../config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE"
  exit 1
fi

# Extract local_recording_dir from config.ini
LOCAL_RECORDING_DIR=$(awk -F= '/^local_recording_dir/ {print $2}' "$CONFIG_FILE" | tr -d '[:space:]')
if [ -z "$LOCAL_RECORDING_DIR" ]; then
  echo "local_recording_dir not found in config.ini. Using default ./zoom_recordings"
  LOCAL_RECORDING_DIR="./zoom_recordings"
fi

mkdir -p "$LOCAL_RECORDING_DIR"

# Set the length of each recording segment (seconds)
SEGMENT_SECS=3600

# Filenames: e.g., zoom_audio_20250328_130000_0001.wav
FILENAME_PATTERN="${LOCAL_RECORDING_DIR}/zoom_audio_%Y%m%d_%H%M%S_%%04d.wav"

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

wait_until_top_of_minute_ms() {
  # Current epoch time in milliseconds
  now_ms=$(date +%s%3N)   # e.g. 1698742412345 (ms)

  # ms past the current minute:
  ms_into_minute=$((now_ms % 60000))

  # Time until top-of-minute
  ms_left=$((60000 - ms_into_minute))
  if [ "$ms_left" -eq 60000 ]; then
    ms_left=0  # already exactly HH:MM:00.000
  fi

  # Convert to fractional seconds
  sec_float=$(awk -v val="$ms_left" 'BEGIN {printf "%.3f", val/1000.0}')

  echo "Current time: $(date +%T.%3N). Sleeping $sec_float second(s) to next full minute..."
  sleep "$sec_float"
}

echo "Waiting for next top-of-minute with ms accuracy..."
wait_until_top_of_minute_ms
echo "Reached top-of-minute. Launching ffmpeg..."

# echo "Waiting for the next top-of-hour boundary with millisecond accuracy..."
# wait_until_top_of_hour_ms
# echo "Reached top-of-hour. Launching ffmpeg..."

# Record from Zoom F8 Pro at 8 channels, 48kHz, 32-bit float
ffmpeg -loglevel info \
    -f alsa \
    -channels 8 \
    -sample_rate 48000 \
    -acodec pcm_f32le \
    -i "hw:2,0" \
    -f segment \
    -segment_time "$SEGMENT_SECS" \
    -segment_format wav \
    -segment_atclocktime 0 \
    -strftime 1 \
    -reset_timestamps 1 \
    -write_bext 1 \
    -rf64 always \
    -metadata creation_time="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
    -metadata coding_history="ZoomF8Pro USB 48kHz/32float" \
    "$FILENAME_PATTERN"
