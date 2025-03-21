#!/bin/bash

# Duration of each file in minutes (edit as needed)
DURATION_MINUTES=1

# Directory where recordings will be saved
OUTPUT_DIR=~/zoom_recordings
mkdir -p "$OUTPUT_DIR"

# Device identifier (from 'arecord -l')
DEVICE="hw:1,0"

# Number of channels (Zoom F8n Pro has 8 channels)
CHANNELS=8
SAMPLE_RATE=48000

# Segment duration in seconds
SEGMENT_DURATION=$(($DURATION_MINUTES * 60))

# Filename pattern for segments
FILENAME_PATTERN="${OUTPUT_DIR}/zoom_audio_%Y%m%d_%H%M%S_%04d.wav"

echo "Recording audio to segmented files with pattern: ${FILENAME_PATTERN}, segment duration: ${DURATION_MINUTES} minute(s)..."

ffmpeg -f alsa \
       -channels $CHANNELS \
       -sample_rate $SAMPLE_RATE \
       -acodec pcm_f32le \
       -i "$DEVICE" \
       -f segment \
       -segment_time $SEGMENT_DURATION \
       -segment_format wav \
       -strftime 1 \
       -reset_timestamps 1 \
       "${FILENAME_PATTERN}"

echo "Recording process started. Files will be segmented in ${DURATION_MINUTES} minute chunks."
echo "Press Ctrl+C to stop recording."

# Keep the script running in the foreground (no while loop needed anymore)
wait