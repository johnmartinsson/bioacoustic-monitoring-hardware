import os
import time
import subprocess
import logging
import configparser

def main():
    # Load configuration
    config = configparser.RawConfigParser()
    config.read('config.ini')
    
    local_recording_dir = config['paths']['local_recording_dir']
    nas_ip = config['network']['nas_ip']
    nas_user = config['network']['nas_user']
    nas_directory = config['paths']['nas_directory']
    sync_log = config['files']['sync_log']
    check_interval = config.getint('settings', 'check_interval_pi')
    log_level = config['logging']['level']
    log_format = config['logging']['format']

    # Setup logging
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger('backup_recordings')

    # Ensure sync_log file exists
    if not os.path.exists(sync_log):
        open(sync_log, 'w').close()

    # Read all previously synced files into a set
    with open(sync_log, 'r') as f:
        synced_files = set(line.strip() for line in f if line.strip())

    logger.info(f"Starting backup_recordings.py. Monitoring directory: {local_recording_dir}")

    while True:
        # If local directory doesn't exist, just wait
        if not os.path.exists(local_recording_dir):
            logger.warning(f"Local recording directory does not exist: {local_recording_dir}")
            time.sleep(check_interval)
            continue

        # Scan for new files
        for filename in os.listdir(local_recording_dir):
            filepath = os.path.join(local_recording_dir, filename)
            # We only consider regular files, skip directories
            if not os.path.isfile(filepath):
                continue
            # Skip if already synced
            if filename in synced_files:
                continue

            # Attempt to rsync the file to the NAS
            logger.info(f"Found new file to sync: {filename}. Initiating rsync to {nas_ip}:{nas_directory}")
            print(f"Syncing file: {filename} to {nas_ip}:{nas_directory}")

            try:
                subprocess.run([
                    'rsync', '-av', filepath, f"{nas_user}@{nas_ip}:{nas_directory}/"
                ], check=True)  # Adjust 'pi@' if needed for your NAS user
                logger.info(f"File {filename} successfully rsynced to {nas_ip}:{nas_directory}")

                # Add to the sync_log so we don't send it again
                with open(sync_log, 'a') as sf:
                    sf.write(filename + '\n')
                synced_files.add(filename)

            except subprocess.CalledProcessError as e:
                logger.error(f"rsync failed for file {filename}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error while syncing file {filename}: {e}")

        time.sleep(check_interval)

if __name__ == '__main__':
    main()
