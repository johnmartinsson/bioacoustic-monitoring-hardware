#!/usr/bin/env python3
"""
backup_recordings.py

A single script to handle audio backup in two modes:

1) --rpi=recordingpi
    - Source: Local SD card (from_audio_dir)
    - Destination: USB drive (to_audio_dir)
    - Includes:
        * SMART check on /dev/sda
        * Verification that the USB drive is mounted
        * Automatic removal of oldest .wav files if local recording directory
          grows beyond max_local_recording_size_gb.

2) --rpi=analyticspi
    - Source: SSHFS-mounted directory from the Recording Pi (from_audio_dir)
    - Destination: NFS-mounted NAS directory (to_audio_dir)
    - Includes:
        * Verification that from_audio_dir and to_audio_dir are mounted
        * rsync of complete .wav files
        * Skips SMART checks and local file-removal routine

General Steps in Both Modes:
  - Determine from_audio_dir and to_audio_dir from config.ini, depending on rpi mode
  - Identify new, "complete" .wav files
  - rsync them to the destination
  - Log successes, warnings, and errors
"""

import sys
import os
import time
import subprocess
import logging
import configparser
import argparse
from pathlib import Path
from datetime import datetime

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Backup recordings either from Recording Pi or Analytics Pi.")
    parser.add_argument("--rpi", required=True, choices=["recordingpi", "analyticspi"],
                        help="Specify which Pi mode to run: 'recordingpi' or 'analyticspi'.")
    return parser.parse_args()


def setup_logging(script_dir: Path) -> None:
    """Configure logging to a file named 'backup_recordings.log' in the script directory."""
    log_file = script_dir / "backup_recordings.log"

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.info("\n-------------------------------------------------------------")
    logging.info("Starting backup_recordings.py script")


def read_config(script_dir: Path) -> configparser.ConfigParser:
    """
    Reads config.ini from the script's directory (or any path you prefer).
    Expects sections like [recordingpi], [analyticspi], and [recording].
    """
    config_path = script_dir / "config.ini"
    if not config_path.is_file():
        logging.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def is_path_on_mounted_fs(path_str: str) -> bool:
    """
    Returns True if 'path_str' is on a mounted filesystem.
    We'll climb up the directory tree until we find a mount point
    or reach the root. If we find a mount point before root, return True.
    """
    p = Path(path_str).resolve()
    while True:
        if os.path.ismount(p):
            return True
        # If we've reached root and haven't found a mount point:
        if p == p.parent:
            return False
        p = p.parent


def run_smart_check(device_path="/dev/sda"):
    """Run a simple SMART health check, logging output. (Recording Pi scenario only.)"""
    logging.info(f"Running SMART health check on {device_path}")
    smart_command = ["smartctl", "-H", device_path]
    try:
        result = subprocess.run(smart_command, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"SMART health check output:\n{result.stdout}")
        else:
            logging.warning(f"SMART check returned code {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}")
    except FileNotFoundError:
        logging.warning("smartctl not installed or not found. Please install smartmontools if needed.")
    except Exception as e:
        logging.error(f"Error running smartctl: {e}")


def check_mount_or_log(path_str: str, label: str) -> bool:
    """
    Ensure 'path_str' is mounted. Return True if mounted,
    False if not. Log an error if it's not mounted.
    """
    if not is_path_on_mounted_fs(path_str):
        logging.error(f"{label} is NOT mounted: {path_str}")
        return False
    return True


def is_file_size_stable(filepath, check_interval=2):
    """Check if the file size is stable (unchanged) over 'check_interval' seconds."""
    initial_size = os.path.getsize(filepath)
    time.sleep(check_interval)
    current_size = os.path.getsize(filepath)
    return (initial_size == current_size)


def is_file_complete(filepath, modification_threshold):
    """
    Consider a file complete if:
      - last modification is older than 'modification_threshold' seconds ago
      - AND file size is stable
    """
    last_modified = os.path.getmtime(filepath)
    if (time.time() - last_modified) > modification_threshold:
        return is_file_size_stable(filepath)
    return False


def run_rsync_list(from_dir: str, to_dir: str, file_list: list, script_dir: Path, synced_files_log: Path):
    """
    Use rsync with --files-from to transfer the listed files from from_dir to to_dir.
    Append newly synced files to synced_files_log if successful.
    """
    temp_list_path = script_dir / "rsync_list.txt"
    with open(temp_list_path, "w", encoding="utf-8") as tf:
        for rp in file_list:
            tf.write(rp + "\n")

    rsync_command = [
        "rsync",
        "-av",
        "--files-from", str(temp_list_path),
        f"{from_dir}/",
        f"{to_dir}/"
    ]
    logging.info(f"Running rsync command: {' '.join(rsync_command)}")
    completed_proc = subprocess.run(rsync_command, capture_output=True, text=True)

    if completed_proc.returncode == 0:
        logging.info("rsync completed successfully for the new .wav files.")
        if completed_proc.stdout:
            logging.info(f"rsync stdout:\n{completed_proc.stdout}")
        if completed_proc.stderr:
            logging.info(f"rsync stderr:\n{completed_proc.stderr}")

        # Mark them as synced.
        with open(synced_files_log, "a", encoding="utf-8") as sf:
            for rp in file_list:
                sf.write(rp + "\n")

    else:
        logging.warning(f"rsync returned non-zero exit code: {completed_proc.returncode}")
        logging.warning(f"rsync stdout:\n{completed_proc.stdout}")
        logging.warning(f"rsync stderr:\n{completed_proc.stderr}")

    # Clean up
    try:
        temp_list_path.unlink()
    except OSError:
        pass


def get_directory_size_gb(dir_path: str) -> float:
    """Return total size of all files under dir_path, in gigabytes."""
    total_bytes = 0
    p = Path(dir_path).resolve()
    if not p.is_dir():
        return 0.0
    for f in p.rglob("*"):
        if f.is_file():
            total_bytes += f.stat().st_size
    return total_bytes / (1024 ** 3)


def remove_oldest_files(dir_path: str, max_size_gb: float):
    """
    Remove the oldest .wav files in dir_path until total size is <= max_size_gb.
    Sort by modification time ascending (oldest first).
    """
    p = Path(dir_path).resolve()
    all_wavs = sorted(p.rglob("*.wav"), key=lambda x: x.stat().st_mtime)

    while True:
        current_size_gb = get_directory_size_gb(str(p))
        if current_size_gb <= max_size_gb:
            break

        if not all_wavs:
            logging.warning("No more .wav files to remove, but still above size limit.")
            break

        oldest_file = all_wavs.pop(0)
        try:
            oldest_file.unlink()
            logging.info(f"Removed oldest file: {oldest_file}")
        except Exception as e:
            logging.error(f"Error removing file {oldest_file}: {e}")


###############################################################################
# MAIN
###############################################################################

def main():
    script_dir = Path(__file__).resolve().parent
    setup_logging(script_dir)
    args = parse_args()
    config = read_config(script_dir)

    rpi_mode = args.rpi  # "recordingpi" or "analyticspi"

    # We'll store settings in the config under the relevant section
    # e.g. config["recordingpi"]["from_audio_dir"], config["recordingpi"]["to_audio_dir"]
    from_audio_dir = config[rpi_mode]["from_audio_dir"]
    to_audio_dir   = config[rpi_mode]["to_audio_dir"]

    # Common recording settings (used for determining "complete" threshold)
    # (You can keep them in a [recording] section or adapt as needed.)
    record_duration = config.getint("recordingpi", "segment_time", fallback=3600)
    modification_threshold = record_duration + 60
    max_local_recording_size_gb = config.getfloat("recordingpi", "max_local_recording_size_gb", fallback=32.0)

    logging.info(f"Running in {rpi_mode} mode.")
    logging.info(f"from_audio_dir = {from_audio_dir}")
    logging.info(f"to_audio_dir   = {to_audio_dir}")
    logging.info(f"record_duration = {record_duration}, so modification_threshold = {modification_threshold}")
    logging.info(f"max_local_recording_size_gb = {max_local_recording_size_gb}")

    # Make sure the directories exist (locally).
    Path(from_audio_dir).mkdir(parents=True, exist_ok=True)
    Path(to_audio_dir).mkdir(parents=True, exist_ok=True)

    ################################################################
    # MODE-SPECIFIC LOGIC
    ################################################################
    if rpi_mode == "recordingpi":
        # 1) Run SMART check on /dev/sda
        #run_smart_check(device_path="/dev/sda")

        # 2) Verify local USB is mounted
        if not check_mount_or_log(to_audio_dir, label="USB backup directory"):
            logging.info("Exiting script because USB drive is not properly mounted.")
            return

        # 3) Log df for the backup directory
        logging.info("Logging df -h for the backup directory (USB):")
        try:
            df_command = ["df", "-h", to_audio_dir]
            df_result = subprocess.run(df_command, capture_output=True, text=True)
            if df_result.returncode == 0:
                logging.info(f"df -h {to_audio_dir}:\n{df_result.stdout}")
            else:
                logging.warning(f"df command returned non-zero exit code: {df_result.returncode}")
                logging.warning(f"df stdout:\n{df_result.stdout}")
                logging.warning(f"df stderr:\n{df_result.stderr}")
        except Exception as e:
            logging.error(f"Error running df command: {e}")

    else:
        # analytics pi
        # We expect from_audio_dir and to_audio_dir to be SSHFS and NFS respectively
        # Check if they're mounted. Optionally try mounting automatically if you want.
        if not check_mount_or_log(from_audio_dir, label="SSHFS from_audio_dir"):
            logging.error("Exiting script because from_audio_dir is not properly mounted on the Analytics Pi.")
            return

        if not check_mount_or_log(to_audio_dir, label="NFS to_audio_dir"):
            logging.error("Exiting script because to_audio_dir (NAS) is not properly mounted on the Analytics Pi.")
            return

    ################################################################
    #  Find new “complete” .wav files, skip previously synced
    ################################################################
    synced_files_log = script_dir / "synced_files.log"
    synced_files = set()
    if synced_files_log.is_file():
        with open(synced_files_log, "r", encoding="utf-8") as sf:
            for line in sf:
                entry = line.strip()
                if entry:
                    synced_files.add(entry)

    # Gather complete unsynced .wav files
    complete_unsynced_files = []
    for fpath in Path(from_audio_dir).rglob("*.wav"):
        rel_path = str(fpath.relative_to(from_audio_dir))  # store as relative path
        if rel_path in synced_files:
            # It's already synced, skip
            continue
        if is_file_complete(fpath, modification_threshold):
            complete_unsynced_files.append(rel_path)
        else:
            # Debug info
            logging.info(f"Skipping incomplete or not-yet-stable file: {fpath}")

    if not complete_unsynced_files:
        logging.info("No new complete .wav files found to sync at this time.")
    else:
        run_rsync_list(from_audio_dir, to_audio_dir, complete_unsynced_files, script_dir, synced_files_log)

    ################################################################
    #  If in recordingpi mode, remove oldest .wav if local size > max
    ################################################################
    if rpi_mode == "recordingpi":
        try:
            current_size_gb = get_directory_size_gb(from_audio_dir)
            logging.info(f"Current size of {from_audio_dir}: {current_size_gb:.2f} GB")

            if current_size_gb > max_local_recording_size_gb:
                logging.info(f"Local recording directory exceeds {max_local_recording_size_gb} GB. Removing oldest .wav files.")
                remove_oldest_files(from_audio_dir, max_local_recording_size_gb)
            else:
                logging.info("Local recording directory is within allowed size limit.")
        except Exception as e:
            logging.error(f"Error checking or trimming local directory size: {e}")

    else:
        # analytics pi => skip removal
        logging.info("Skipping local file-removal routine in analytics pi mode.")

    logging.info("Finished backup_recordings.py script.")


if __name__ == "__main__":
    main()
