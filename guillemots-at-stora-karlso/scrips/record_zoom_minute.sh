#!/usr/bin/env bash
#
# continuous_minute_test.sh
#
#  1) Wait until top-of-minute with millisecond accuracy
#  2) Start a single ffmpeg process that streams 8-channel float audio
#     from the Zoom F8 Pro over USB
#  3) Segment the audio in 1-hour chunks (or whatever chunk size you choose),
#     each chunk with BEXT metadata, no sample gaps.
#
#  Adjust as needed (device name, segment length, output dir, etc.)

############################
# USER CONFIG
############################

DEVICE="hw:2,0"          # 'arecord -l' to identify your Zoom F8 Pro device
CHANNELS=8
SAMPLE_RATE=48000
OUTPUT_DIR="./zoom_recordings"
mkdir -p "$OUTPUT_DIR"

# Segment duration in seconds (defaults to 1 hour = 3600)
# For quick testing, you might set SEGMENT_SECS=60 or 120, etc.
SEGMENT_SECS=3600

# Filename pattern. %Y,%m,%d,%H,%M,%S = local date/time
# %04d = 4-digit segment index
FILENAME_PATTERN="${OUTPUT_DIR}/zoom_audio_%Y%m%d_%H%M%S_%04d.wav"

############################
# 1) WAIT UNTIL TOP-OF-MINUTE W/MS ACCURACY
############################

# wait_until_top_of_minute_ms() {
#   # Current epoch time in milliseconds
#   now_ms=$(date +%s%3N)   # e.g. 1698742412345 (ms)

#   # ms past the current minute:
#   ms_into_minute=$((now_ms % 60000))

#   # Time until top-of-minute
#   ms_left=$((60000 - ms_into_minute))
#   if [ "$ms_left" -eq 60000 ]; then
#     ms_left=0  # already exactly HH:MM:00.000
#   fi

#   # Convert to fractional seconds
#   sec_float=$(awk -v val="$ms_left" 'BEGIN {printf "%.3f", val/1000.0}')

#   echo "Current time: $(date +%T.%3N). Sleeping $sec_float second(s) to next full minute..."
#   sleep "$sec_float"
# }

# echo "Waiting for the next full minute boundary with ms accuracy..."
# wait_until_top_of_minute_ms
echo "Reached top-of-minute. Launching ffmpeg..."

############################
# 2) START A SINGLE FFMPEG PROCESS
############################
# 
#  -f segment: splits the output into segments
#  -segment_time $SEGMENT_SECS: each chunk length
#  -strftime 1: put date/time in each chunk’s filename
#  -reset_timestamps 1: resets output timestamps in each segment
#  -write_bext 1 + -rf64 always: produce BWF (RF64) for large-file
#  -metadata creation_time=...  : embed approximate creation time in each chunk's BEXT

ffmpeg -loglevel info \
    -f alsa \
    -channels "$CHANNELS" \
    -sample_rate "$SAMPLE_RATE" \
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