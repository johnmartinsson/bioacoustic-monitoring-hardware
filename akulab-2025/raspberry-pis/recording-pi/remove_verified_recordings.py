import os
import time
import logging
import configparser

def main():
    # Load configuration
    config = configparser.RawConfigParser()
    config.read('config.ini')

    local_recording_dir = config['paths']['local_recording_dir']
    verified_files_log = config['files']['verified_files_log']
    check_interval = config.getint('settings', 'check_interval_pi')
    max_local_files = config.getint('settings', 'max_local_files')
    log_level = config['logging']['level']
    log_format = config['logging']['format']

    # Setup logging
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger('remove_verified_recordings')

    # Ensure verified_files_log exists
    if not os.path.exists(verified_files_log):
        open(verified_files_log, 'w').close()

    logger.info(f"Starting remove_verified_recordings.py. Will keep up to {max_local_files} verified recordings.")

    while True:
        # Load the set of verified filenames
        with open(verified_files_log, 'r') as vf:
            verified_files = set(line.strip() for line in vf if line.strip())

        # Gather the existing verified files in local_recording_dir
        existing_verified_files = []
        for fname in verified_files:
            path = os.path.join(local_recording_dir, fname)
            if os.path.isfile(path):
                existing_verified_files.append(path)

        # If we have more verified recordings locally than allowed, remove oldest
        if len(existing_verified_files) > max_local_files:
            logger.info(f"Found {len(existing_verified_files)} verified recordings (limit={max_local_files}). Removing oldest.")
            # Sort by modification time ascending
            existing_verified_files.sort(key=lambda x: os.path.getmtime(x))
            num_to_remove = len(existing_verified_files) - max_local_files
            to_remove = existing_verified_files[:num_to_remove]

            for filepath in to_remove:
                try:
                    os.remove(filepath)
                    logger.info(f"Removed old verified recording: {filepath}")
                    print(f"Removed old verified recording: {filepath}")
                except OSError as e:
                    logger.error(f"Failed to remove file {filepath}: {e}")

        time.sleep(check_interval)

if __name__ == '__main__':
    main()
