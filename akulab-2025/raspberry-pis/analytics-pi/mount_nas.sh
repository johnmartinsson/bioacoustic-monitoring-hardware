#!/usr/bin/env bash

# Load configuration from config.ini
CONFIG_FILE="$(dirname "$0")/../../config.ini"
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
NAS_IP=$(read_config "nas_ip")
NAS_USER=$(read_config "nas_user")
NAS_AUDIO_DIR=$(read_config "nas_audio_dir")

# Ensure the local mount point exists
mkdir -p "$NAS_AUDIO_DIR"

# Mount the NAS directory
echo "Mounting NAS directory from ${NAS_IP} to ${NAS_AUDIO_DIR}..."
# sudo mount -t nfs "${NAS_IP}:/nas_directory" "$NAS_AUDIO_DIR"

# if [ $? -eq 0 ]; then
#   echo "NAS directory mounted successfully."
# else
#   echo "Failed to mount NAS directory."
# fi