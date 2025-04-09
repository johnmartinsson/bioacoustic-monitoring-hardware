#!/usr/bin/env python3

"""
backup_recordings.py

A script to:
  1) Run a SMART health check on your external USB drive (e.g. /dev/sda),
     logging results (requires 'smartmontools' installed).
  2) Verify the backup directory is on a mounted filesystem
     (e.g. /media/recordingpi/Elements is the actual mount point).
  3) Rsync new .wav files from local_recording_dir to local_backup_recording_dir using checksums.
     - Unchanged files are not resent or duplicated.
  4) Keep a log of success/failure.
  5) Check local_recording_dir size and if it exceeds max_local_recording_size_gb,
     remove oldest .wav files to reclaim space.
  6) Log disk usage (via df -h) for the backup directory.
"""

import os
import sys
import subprocess
import logging
import configparser
from pathlib import Path
from datetime import datetime

def main():
    script_dir = Path(__file__).resolve().parent
    log_file = script_dir / "backup_recordings.log"

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.info("Starting backup_recordings.py script...")

    # ----------------------------------------------------------------
    # 1. Read config.ini
    # ----------------------------------------------------------------
    config_path = script_dir / "config.ini"
    if not config_path.is_file():
        logging.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    local_recording_dir = config.get("paths", "local_recording_dir", fallback="/home/pi/local_recordings")
    local_backup_recording_dir = config.get("paths", "local_backup_recording_dir", fallback="/media/recordingpi/Elements/akulab_2025/audio")
    max_local_recording_size_gb = config.getfloat("recording", "max_local_recording_size_gb", fallback=256.0)

    logging.info(f"local_recording_dir = {local_recording_dir}")
    logging.info(f"local_backup_recording_dir = {local_backup_recording_dir}")
    logging.info(f"max_local_recording_size_gb = {max_local_recording_size_gb}")

    # ----------------------------------------------------------------
    # 2. Ensure directories exist
    # ----------------------------------------------------------------
    Path(local_recording_dir).mkdir(parents=True, exist_ok=True)
    Path(local_backup_recording_dir).mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # 3. SMART health check for external drive (adjust /dev/sda as needed)
    # ----------------------------------------------------------------
    device_path = "/dev/sda"  # Replace with actual device if different
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

    # ----------------------------------------------------------------
    # 4. Verify the backup directory is on a mounted filesystem
    #    We'll climb up the path tree until we find a mount point.
    #    If none found, or top is root, we consider not mounted.
    # ----------------------------------------------------------------
    if not is_path_on_mounted_fs(local_backup_recording_dir):
        logging.warning(f"Backup directory not on a mounted filesystem: {local_backup_recording_dir}")
        logging.info("Exiting script because backup drive is not properly mounted.")
        return

    # ----------------------------------------------------------------
    # 5. Log disk usage for the backup mount
    # ----------------------------------------------------------------
    logging.info("Logging df -h for the backup directory:")
    try:
        df_command = ["df", "-h", local_backup_recording_dir]
        df_result = subprocess.run(df_command, capture_output=True, text=True)
        if df_result.returncode == 0:
            logging.info(f"df -h {local_backup_recording_dir}:\n{df_result.stdout}")
        else:
            logging.warning(f"df command returned non-zero exit code: {df_result.returncode}")
            logging.warning(f"df stdout:\n{df_result.stdout}")
            logging.warning(f"df stderr:\n{df_result.stderr}")
    except Exception as e:
        logging.error(f"Error running df command: {e}")

    # ----------------------------------------------------------------
    # 6. Rsync .wav files from local_recording_dir to local_backup_recording_dir
    #    using checksums. Unchanged files will not be re-transferred.
    # ----------------------------------------------------------------
    rsync_command = [
        "rsync",
        "-av",
        "--checksum",
        "--include", "*.wav",     # only .wav
        "--include", "*/",
        "--exclude", "*",         # exclude everything else
        f"{local_recording_dir}/",
        f"{local_backup_recording_dir}/"
    ]

    logging.info(f"Running rsync command: {' '.join(rsync_command)}")

    try:
        completed_proc = subprocess.run(
            rsync_command,
            capture_output=True,
            text=True
        )
        if completed_proc.returncode == 0:
            logging.info("rsync completed successfully (new/changed .wav files transferred).")
            if completed_proc.stdout:
                logging.info(f"rsync stdout:\n{completed_proc.stdout}")
            if completed_proc.stderr:
                logging.info(f"rsync stderr:\n{completed_proc.stderr}")
        else:
            logging.warning(f"rsync returned non-zero exit code: {completed_proc.returncode}")
            logging.warning(f"rsync stdout:\n{completed_proc.stdout}")
            logging.warning(f"rsync stderr:\n{completed_proc.stderr}")
    except Exception as e:
        logging.error(f"Error running rsync: {e}")
        return

    # ----------------------------------------------------------------
    # 7. Check local_recording_dir size; remove oldest .wav if exceeds limit
    # ----------------------------------------------------------------
    try:
        current_size_gb = get_directory_size_gb(local_recording_dir)
        logging.info(f"Current size of {local_recording_dir}: {current_size_gb:.2f} GB")

        if current_size_gb > max_local_recording_size_gb:
            logging.info(
                f"Local recording directory exceeds {max_local_recording_size_gb} GB. Removing oldest .wav files."
            )
            remove_oldest_files(local_recording_dir, max_local_recording_size_gb)
        else:
            logging.info("Local recording directory is within allowed size limit.")
    except Exception as e:
        logging.error(f"Error checking or trimming local directory size: {e}")

    logging.info("Finished backup_recordings.py script.")


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
            # we are at the top
            return False
        p = p.parent


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
            # Move on to the next if removal fails.


if __name__ == "__main__":
    main()

