import os
import time
import hashlib
import logging

# Configuration
NAS_DIRECTORY = "simulated_nas_storage"
SYNCED_FILES_LOG = "nas_synced_files.log"
VERIFICATION_CHANNEL = "verification_channel.txt"  # Shared file for verification status
CHECK_INTERVAL_NAS = 1  # seconds

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NAS Server - %(levelname)s - %(message)s')

def calculate_hash(filepath):
    """Calculates SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as file:
        while True:
            chunk = file.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def monitor_nas_directory():
    """Monitors the NAS directory for new files and verifies them."""
    synced_files = set() # Keep track of files already synced
    if os.path.exists(SYNCED_FILES_LOG):
        with open(SYNCED_FILES_LOG, 'r') as log_file:
            for line in log_file:
                synced_files.add(line.strip())

    logging.info(f"NAS Server monitoring directory: {NAS_DIRECTORY}")

    while True:
        for filename in os.listdir(NAS_DIRECTORY):
            filepath = os.path.join(NAS_DIRECTORY, filename)
            if os.path.isfile(filepath) and filename not in synced_files:
                logging.info(f"New file detected on NAS: {filename}")
                file_hash = calculate_hash(filepath)
                logging.info(f"Calculated hash for {filename}: {file_hash}")

                # Simulate sending hash to Raspberry Pi (using shared file)
                with open(VERIFICATION_CHANNEL, 'w') as channel_file:
                    channel_file.write(f"{filename}:{file_hash}")
                logging.info(f"Sent hash for {filename} to Raspberry Pi via {VERIFICATION_CHANNEL}")

                synced_files.add(filename)
                with open(SYNCED_FILES_LOG, 'a') as log_file:
                    log_file.write(filename + '\n')
                logging.info(f"File {filename} processed and logged.")

        time.sleep(CHECK_INTERVAL_NAS)

if __name__ == "__main__":
    os.makedirs(NAS_DIRECTORY, exist_ok=True)
    if not os.path.exists(VERIFICATION_CHANNEL):
        open(VERIFICATION_CHANNEL, 'w').close() # Create verification channel if it doesn't exist
    monitor_nas_directory()