import os
import shutil
import hashlib
import logging
import time
import signal
import sys
import configparser

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
RECORDING_PI_AUDIO_DIR = config['paths']['recording_pi_dir']
NAS_AUDIO_DIR = config['paths']['nas_dir']
SYNC_LOG = config['paths']['sync_log']
VERIFIED_FILES_LOG = config['paths']['verified_files_log']
CHECK_INTERVAL = config.getint('settings', 'check_interval')
MODIFICATION_THRESHOLD = config.getint('settings', 'modification_threshold')
MAX_RETRIES = config.getint('settings', 'max_retries', fallback=3)
DRY_RUN = config.getboolean('settings', 'dry_run', fallback=False)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("analytics_pi")


def calculate_hash(filepath, buffer_size=65536):
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(buffer_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_file_complete(filepath):
    """Check if a file is complete by checking its modification time."""
    last_modified = os.path.getmtime(filepath)
    return (time.time() - last_modified) > MODIFICATION_THRESHOLD


def retry_operation(operation, *args, retries=MAX_RETRIES, **kwargs):
    """Retry an operation multiple times in case of failure."""
    for attempt in range(retries):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)  # Wait before retrying
    logger.error(f"Operation failed after {retries} attempts.")
    return None


def safe_remove(filepath):
    """Remove a file, respecting dry-run mode."""
    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would remove: {filepath}")
    else:
        os.remove(filepath)


def handle_shutdown(signal, frame):
    """Handle graceful shutdown on SIGINT or SIGTERM."""
    logger.info("Shutting down gracefully...")
    sys.exit(0)


def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Ensure directories for log files exist
    for directory in [os.path.dirname(SYNC_LOG), os.path.dirname(VERIFIED_FILES_LOG)]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Ensure log files exist
    for log_file in [SYNC_LOG, VERIFIED_FILES_LOG]:
        if not os.path.exists(log_file):
            open(log_file, 'w').close()

    # Load synced and verified files
    with open(SYNC_LOG, 'r') as f:
        synced_files = set(line.strip() for line in f if line.strip())
    with open(VERIFIED_FILES_LOG, 'r') as f:
        verified_files = set(line.strip() for line in f if line.strip())

    logger.info("Starting analytics_pi script. Monitoring Recording Pi and NAS directories.")

    cleaned_files = set()

    while True:
        # Scan for new files on the Recording Pi
        for filename in os.listdir(RECORDING_PI_AUDIO_DIR):
            recording_pi_path = os.path.join(RECORDING_PI_AUDIO_DIR, filename)
            nas_path = os.path.join(NAS_AUDIO_DIR, filename)

            # Skip directories or already processed files
            if not os.path.isfile(recording_pi_path) or filename in synced_files:
                continue

            # Skip incomplete files
            if not is_file_complete(recording_pi_path):
                logger.info(f"File {filename} is not complete yet. Skipping.")
                continue

            # Transfer file to NAS
            if retry_operation(shutil.copy2, recording_pi_path, nas_path) is None:
                continue
            synced_files.add(filename)
            with open(SYNC_LOG, 'a') as f:
                f.write(filename + '\n')
            logger.info(f"File {filename} successfully transferred to NAS.")

            # Verify file integrity
            try:
                logger.info(f"Verifying file {filename} integrity.")
                recording_pi_hash = retry_operation(calculate_hash, recording_pi_path)
                nas_hash = retry_operation(calculate_hash, nas_path)
                if recording_pi_hash is None or nas_hash is None:
                    continue
                if recording_pi_hash == nas_hash:
                    logger.info(f"File {filename} verified successfully.")
                    verified_files.add(filename)
                    with open(VERIFIED_FILES_LOG, 'a') as f:
                        f.write(filename + '\n')
                else:
                    logger.error(f"File {filename} verification failed. Hash mismatch.")
            except Exception as e:
                logger.error(f"Failed to verify file {filename}: {e}")
                continue

        # Cleanup verified files from the Recording Pi
        for filename in verified_files:
            if filename in cleaned_files:
                continue
            recording_pi_path = os.path.join(RECORDING_PI_AUDIO_DIR, filename)
            if os.path.exists(recording_pi_path):
                try:
                    safe_remove(recording_pi_path)
                    logger.info(f"Removed verified file {filename} from Recording Pi.")
                    cleaned_files.add(filename)
                except Exception as e:
                    logger.error(f"Failed to remove file {filename} from Recording Pi: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()