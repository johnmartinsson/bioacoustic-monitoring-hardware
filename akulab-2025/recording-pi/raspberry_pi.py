import os
import time
import shutil
import hashlib
import logging

# Configuration
ZOOM_STORAGE_DIRECTORY = "simulated_zoom_storage"
NAS_DIRECTORY = "simulated_nas_storage"
ZOOM_SDCARD_MOUNT_POINT = "simulated_zoom_sdcard" # Simulated mount point
SYNC_LOG_FILE = "raspberry_pi_sync.log"
VERIFICATION_CHANNEL = "verification_channel.txt" # Shared file for verification status
CHECK_INTERVAL_PI = 1  # seconds
DELETE_AFTER_VERIFICATION = True # Enable or disable file deletion after successful sync

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Raspberry Pi - %(levelname)s - %(message)s')

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

def sync_and_verify_files():
    """Monitors Zoom storage, syncs new files to NAS, and verifies."""
    synced_files = set() # Keep track of files already synced
    if os.path.exists(SYNC_LOG_FILE):
        with open(SYNC_LOG_FILE, 'r') as log_file:
            for line in log_file:
                synced_files.add(line.strip())

    logging.info(f"Raspberry Pi monitoring Zoom storage: {ZOOM_SDCARD_MOUNT_POINT} (simulated)")

    while True:
        zoom_sdcard_path = os.path.join(ZOOM_SDCARD_MOUNT_POINT, ZOOM_STORAGE_DIRECTORY) # Simulate SD card mount
        if not os.path.exists(zoom_sdcard_path):
            logging.warning(f"Simulated Zoom SD card directory not found: {zoom_sdcard_path}. Please check if zoom_f8.py is running and created it.")
            time.sleep(CHECK_INTERVAL_PI)
            continue

        for filename in os.listdir(zoom_sdcard_path):
            source_filepath = os.path.join(zoom_sdcard_path, filename)
            if os.path.isfile(source_filepath) and filename not in synced_files:
                destination_filepath = os.path.join(NAS_DIRECTORY, filename)
                logging.info(f"New file detected on Zoom: {filename}. Starting sync to NAS...")

                try:
                    shutil.copy2(source_filepath, destination_filepath) # copy2 preserves metadata
                    logging.info(f"File {filename} copied to NAS: {destination_filepath}")

                    # Calculate hash after copy
                    pi_hash = calculate_hash(destination_filepath)
                    logging.info(f"Calculated hash (Raspberry Pi) for {filename}: {pi_hash}")

                    # Get hash from NAS Server (via shared file) and verify
                    time.sleep(2) # Wait for NAS server to process and write hash
                    nas_verification_data = None
                    if os.path.exists(VERIFICATION_CHANNEL):
                        with open(VERIFICATION_CHANNEL, 'r') as channel_file:
                            nas_verification_data = channel_file.read().strip()
                    else:
                        logging.warning(f"Verification channel file {VERIFICATION_CHANNEL} not found!")
                        nas_verification_data = None

                    if nas_verification_data:
                        nas_filename, nas_hash = nas_verification_data.split(':', 1)
                        if filename == nas_filename and pi_hash == nas_hash:
                            logging.info(f"Verification successful for {filename}! Hashes match.")
                            verification_status = "SUCCESS"
                        else:
                            logging.error(f"Verification FAILED for {filename}! Hashes do not match or filename mismatch.")
                            verification_status = "FAILED"
                    else:
                        logging.warning(f"No verification data received from NAS for {filename}.")
                        verification_status = "NO_NAS_DATA"

                    synced_files.add(filename)
                    with open(SYNC_LOG_FILE, 'a') as log_file:
                        log_file.write(filename + '\n')
                    logging.info(f"File {filename} sync and verification process completed. Status: {verification_status}. Logged sync.")

                    if DELETE_AFTER_VERIFICATION and verification_status == "SUCCESS":
                        try:
                            os.remove(source_filepath)
                            logging.info(f"Deleted source file {filename} from simulated Zoom storage after successful verification.")
                        except OSError as e:
                            logging.error(f"Error deleting source file {filename}: {e}")


                except Exception as e:
                    logging.error(f"Error syncing file {filename} to NAS: {e}")

        time.sleep(CHECK_INTERVAL_PI)


if __name__ == "__main__":
    os.makedirs(ZOOM_SDCARD_MOUNT_POINT, exist_ok=True) # Simulate SD card mount point
    os.makedirs(NAS_DIRECTORY, exist_ok=True) # NAS directory will be created by nas_server.py but ensure it exists here too
    if not os.path.exists(VERIFICATION_CHANNEL):
        open(VERIFICATION_CHANNEL, 'w').close() # Create verification channel if it doesn't exist
    sync_and_verify_files()