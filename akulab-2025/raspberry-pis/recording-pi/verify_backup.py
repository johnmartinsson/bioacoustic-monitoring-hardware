import os
import time
import hashlib
import logging
import configparser

def calculate_hash(filepath):
    """Calculates SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    # Load configuration
    config = configparser.RawConfigParser()
    config.read('config.ini')
    
    local_recording_dir = config['paths']['local_recording_dir']
    verification_channel = config['paths']['verification_channel']
    verified_files_log = config['files']['verified_files_log']
    check_interval = config.getint('recording', 'record_duration')
    log_level = config['logging']['level']
    log_format = config['logging']['format']

    # Setup logging
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger('verify_backup')

    # Ensure verified_files_log file exists
    if not os.path.exists(verified_files_log):
        open(verified_files_log, 'w').close()

    # Load all previously verified filenames
    with open(verified_files_log, 'r') as f:
        verified_files = set(line.strip() for line in f if line.strip())

    logger.info(f"Starting verify_backup.py. Watching verification channel: {verification_channel}")

    last_verification_data = ""

    while True:
        if os.path.exists(verification_channel):
            with open(verification_channel, 'r') as channel:
                data = channel.read().strip()

            # If new data has appeared
            if data and data != last_verification_data:
                last_verification_data = data
                logger.info(f"New verification data received: {data}")
                parts = data.split(':', 1)
                if len(parts) == 2:
                    nas_filename, nas_hash = parts
                    local_filepath = os.path.join(local_recording_dir, nas_filename)

                    if not os.path.isfile(local_filepath):
                        logger.warning(f"File {nas_filename} not found locally. Cannot verify.")
                    else:
                        # Calculate local hash
                        local_hash = calculate_hash(local_filepath)
                        if local_hash == nas_hash:
                            logger.info(f"Verification SUCCESS for {nas_filename}. Hashes match.")
                            print(f"Verification SUCCESS for {nas_filename} - Hash: {nas_hash}")
                            # Mark the file as verified if not already
                            if nas_filename not in verified_files:
                                with open(verified_files_log, 'a') as vf:
                                    vf.write(nas_filename + '\n')
                                verified_files.add(nas_filename)
                        else:
                            logger.error(f"Verification FAILED for {nas_filename}. Hash mismatch.")
                            print(f"Verification FAILED for {nas_filename}.")
                else:
                    logger.warning("Verification channel data is malformed. Expected 'filename:hash'")

        time.sleep(check_interval)

if __name__ == '__main__':
    main()
