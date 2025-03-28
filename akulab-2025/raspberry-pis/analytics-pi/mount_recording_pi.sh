#!/usr/bin/env bash

# Load configuration from config.ini
CONFIG_FILE="$(dirname "$0")/config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE"
  exit 1
fi

# Function to read configuration parameters
read_config() {
  local key=$1
  awk -F= -v key="$key" '$1 ~ key {print $2}' "$CONFIG_FILE" | tr -d '[:space:]'
}

# Read configuration values
RECORDING_PI_IP=$(read_config "recording_pi_ip")
RECORDING_PI_USER=$(read_config "recording_pi_user")
RECORDING_PI_AUDIO_DIR=$(read_config "recording_pi_audio_dir")
RECORDING_PI_REMOTE_DIR=$(read_config "recording_pi_remote_dir")

# Ensure the local mount point exists
mkdir -p "$RECORDING_PI_AUDIO_DIR"

# Mount the Recording Pi directory
echo "Mounting Recording Pi directory from ${RECORDING_PI_USER}@${RECORDING_PI_IP}:${RECORDING_PI_REMOTE_DIR} to ${RECORDING_PI_AUDIO_DIR}..."
sshfs "${RECORDING_PI_USER}@${RECORDING_PI_IP}:${RECORDING_PI_REMOTE_DIR}" "$RECORDING_PI_AUDIO_DIR"

if [ $? -eq 0 ]; then
  echo "Recording Pi directory mounted successfully."
else
  echo "Failed to mount Recording Pi directory."
fi