#!/usr/bin/env python3

"""
backup_recordings.py

A script to:
  1) Run a SMART health check on your external USB drive (e.g. /dev/sda),
     logging results (requires 'smartmontools' installed).
  2) Verify the backup directory is on a mounted filesystem
     (e.g. /media/recordingpi/Elements is the actual mount point).
  3) Rsync only *complete* .wav files (time since last mod > threshold + size stable),
     excluding any files already listed in synced_files.log. This avoids re-transfer
     and avoids expensive checksums.
  4) Keep a log of success/failure.
  5) Check local_recording_dir size and if it exceeds max_local_recording_size_gb,
     remove oldest .wav files to reclaim space.
  6) Log disk usage (via df -h) for the backup directory.

Notes:
- “Complete” threshold = record_duration + 60 seconds (configurable in config.ini).
- Once a file is successfully synced, it’s recorded in synced_files.log and will be skipped next time,
  unless you manually remove it from that list.
- We use rsync with -av (archive + verbose) so that only genuinely new or changed files transfer.
  Without --checksum, rsync compares mtime + size, which is much faster than reading the whole file.
"""

import os
import sys
import time
import subprocess
import logging
import configparser
from pathlib import Path
from datetime import datetime

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

    # We'll read record_duration so we can set the “complete” threshold:
    record_duration = config.getint("recording", "record_duration", fallback=3600)
    modification_threshold = record_duration + 60

    logging.info(f"local_recording_dir = {local_recording_dir}")
    logging.info(f"local_backup_recording_dir = {local_backup_recording_dir}")
    logging.info(f"max_local_recording_size_gb = {max_local_recording_size_gb}")
    logging.info(f"record_duration = {record_duration}, so modification_threshold = {modification_threshold} seconds")

    # ----------------------------------------------------------------
    # 2. Ensure directories exist
    # ----------------------------------------------------------------
    Path(local_recording_dir).mkdir(parents=True, exist_ok=True)
    Path(local_backup_recording_dir).mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # 3. SMART health check for external drive (adjust /dev/sda as needed)
    # ----------------------------------------------------------------
    device_path = "/dev/sda"  # Replace if different
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
    # 6. Collect only “complete” .wav files, skipping any that are in synced_files.log
    # ----------------------------------------------------------------
    synced_files_log = script_dir / "synced_files.log"
    synced_files = set()

    # Load existing synced filenames (one per line)
    if synced_files_log.is_file():
        with open(synced_files_log, "r", encoding="utf-8") as sf:
            for line in sf:
                entry = line.strip()
                if entry:
                    synced_files.add(entry)

    # Gather complete .wav files that are not in synced_files
    complete_unsynced_files = []
    for fpath in Path(local_recording_dir).rglob("*.wav"):
        rel_path = str(fpath.relative_to(local_recording_dir))  # store as relative path
        if rel_path in synced_files:
            # It's already in synced_files.log, skip
            continue
        if is_file_complete(fpath, modification_threshold):
            complete_unsynced_files.append(rel_path)
        else:
            # debug info
            logging.info(f"Skipping incomplete or not-yet-stable file: {fpath}")

    if not complete_unsynced_files:
        logging.info("No new complete .wav files found to sync at this time.")
    else:
        # Write those to a temporary file for rsync --files-from
        temp_list_path = script_dir / "rsync_list.txt"
        with open(temp_list_path, "w", encoding="utf-8") as tf:
            for rp in complete_unsynced_files:
                tf.write(rp + "\n")

        rsync_command = [
            "rsync",
            "-av",           # archive + verbose, no --checksum
            "--files-from", str(temp_list_path),
            f"{local_recording_dir}/",    # source base
            f"{local_backup_recording_dir}/"
        ]

        logging.info(f"Running rsync command: {' '.join(rsync_command)}")
        completed_proc = subprocess.run(rsync_command, capture_output=True, text=True)
        if completed_proc.returncode == 0:
            logging.info("rsync completed successfully for the new .wav files.")
            # rsync stdout lines that say "filename" => means it was updated or created
            # We can log them or rely on user reading the log. We do both:
            if completed_proc.stdout:
                logging.info(f"rsync stdout:\n{completed_proc.stdout}")
            if completed_proc.stderr:
                logging.info(f"rsync stderr:\n{completed_proc.stderr}")

            # If successful, add them to synced_files
            with open(synced_files_log, "a", encoding="utf-8") as sf:
                for rp in complete_unsynced_files:
                    sf.write(rp + "\n")
                    synced_files.add(rp)

        else:
            logging.warning(f"rsync returned non-zero exit code: {completed_proc.returncode}")
            logging.warning(f"rsync stdout:\n{completed_proc.stdout}")
            logging.warning(f"rsync stderr:\n{completed_proc.stderr}")

        # Clean up the temporary list
        try:
            temp_list_path.unlink()
        except OSError:
            pass

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


if __name__ == "__main__":
    main()
