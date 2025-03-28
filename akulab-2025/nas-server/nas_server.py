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
    config = configparser.ConfigParser()
    config.read('config.ini')

    nas_directory = config['paths']['nas_directory']
    synced_files_log_nas = config['files']['synced_files_log_nas']
    verification_channel = config['paths']['verification_channel']
    check_interval = config.getint('settings', 'check_interval_nas')
    log_level = config['logging']['level']
    log_format = config['logging']['format']

    # Setup logging
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger('nas_server')

    if not os.path.exists(nas_directory):
        os.makedirs(nas_directory)

    if not os.path.exists(verification_channel):
        open(verification_channel, 'w').close()

    if not os.path.exists(synced_files_log_nas):
        open(synced_files_log_nas, 'w').close()

    # Keep track of files we've already processed
    with open(synced_files_log_nas, 'r') as f:
        processed_files = set(line.strip() for line in f if line.strip())

    logger.info(f"NAS Server monitoring directory: {nas_directory}")

    while True:
        for filename in os.listdir(nas_directory):
            filepath = os.path.join(nas_directory, filename)
            if os.path.isfile(filepath) and filename not in processed_files:
                logger.info(f"New file detected on NAS: {filename}")
                file_hash = calculate_hash(filepath)
                logger.info(f"Calculated hash for {filename}: {file_hash}")

                # Write this file’s hash to the shared verification channel
                with open(verification_channel, 'w') as channel:
                    channel.write(f"{filename}:{file_hash}")
                logger.info(f"Sent hash for {filename} to Raspberry Pi via {verification_channel}")

                processed_files.add(filename)
                with open(synced_files_log_nas, 'a') as pf:
                    pf.write(filename + '\n')
                logger.info(f"File {filename} processed and logged.")

        time.sleep(check_interval)

if __name__ == '__main__':
    main()
