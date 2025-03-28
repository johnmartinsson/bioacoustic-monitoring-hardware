#!/usr/bin/env bash
#
# continuous_hourly.sh
# 
# 1) Wait until top-of-hour with millisecond accuracy
# 2) Start a single ffmpeg process that streams 8-channel float audio
#    from the Zoom F8 Pro as a USB interface
# 3) Segment the audio in 1-hour chunks with BEXT metadata, 
#    each chunk exactly one hour long, no sample drops.
#
# Adjust as needed for your environment (device name, output path, etc.)

############################
# USER CONFIG
############################

DEVICE="hw:2,0"                   # 'arecord -l' to identify your Zoom F8 Pro device
CHANNELS=8
SAMPLE_RATE=48000
OUTPUT_DIR="./zoom_recordings"    # Directory where recordings will be saved
mkdir -p "$OUTPUT_DIR"

# One-hour segments:
SEGMENT_SECS=3600

# Name pattern. %Y, %m, %d, %H, %M, %S are replaced by local date/time.
# The '%04d' will be replaced by the segment number (0001, 0002, ...).
# Example final filename => zoom_audio_20231031_120000_0001.wav
FILENAME_PATTERN="${OUTPUT_DIR}/zoom_audio_%Y%m%d_%H%M%S_%04d.wav"

############################
# 1) WAIT UNTIL THE NEXT TOP-OF-HOUR WITH MS ACCURACY
############################

wait_until_top_of_hour_ms() {
  # Current epoch time in milliseconds
  now_ms=$(date +%s%3N)            # e.g. 1698742412345 (ms)
  # Current second-of-hour
  #   hours_since_epoch = now_ms // 3600000
  #   ms_into_hour = now_ms % 3600000
  ms_into_hour=$((now_ms % 3600000))

  # If ms_into_hour = ms past the hour, time until top-of-hour:
  ms_left=$((3600000 - ms_into_hour))
  if [ $ms_left -eq 3600000 ]; then
    # We are already at HH:00:00 precisely (to the ms), so no wait
    ms_left=0
  fi

  # Convert ms_left to decimal seconds for 'sleep', e.g. 1234 => 1.234
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

# echo "Waiting for the next top-of-hour boundary with millisecond accuracy..."
wait_until_top_of_hour_ms
echo "Reached top-of-hour. Launching ffmpeg..."

############################
# 2) START A SINGLE FFMPEG PROCESS
############################
#
# -f alsa -i "$DEVICE": read 8ch float audio from Zoom F8 Pro
# -f segment: segment the output into hour-chunks
# -segment_time $SEGMENT_SECS: each chunk is 3600s
# -strftime 1: filename uses date/time placeholders
# -reset_timestamps 1: reset segment timestamps to 0 each time
# -metadata creation_time=...  : Insert a “creation_time” in BEXT
# -write_bext 1 -rf64 always: produce standard broadcast WAV with large-file support

ffmpeg -loglevel info \
    -f alsa \
    -channels $CHANNELS \
    -sample_rate $SAMPLE_RATE \
    -acodec pcm_f32le \
    -i "$DEVICE" \
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
