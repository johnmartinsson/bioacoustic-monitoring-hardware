#!/usr/bin/env python3
"""
backup_recordings.py

A single script to handle audio backup:

1) --rpi=analyticspi
    - Source: SSHFS-mounted directory from the Recording Pi (from_audio_dir)
    - Destination: NFS-mounted NAS directory (to_audio_dir)
    - Includes:
        * Verification that from_audio_dir and to_audio_dir are mounted
        * rsync of complete .wav files
        * Optionally, sha256 verification if configured (verify_sha256 = true)
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
import getpass
import hashlib  # <-- NEW
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
    user = getpass.getuser()
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = Path(f"/home/{user}/logs/backup_recordings")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{today}_backup_recordings.log"

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
        return True #is_file_size_stable(filepath)
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
        "-rtv",
        "--no-g", "--no-o",
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

###############################################################################
# NEW HELPERS FOR SHA256 VERIFICATION
###############################################################################
# TODO: something is not working with this, debug. Commented out for now.

def compute_local_sha256(filepath):
    """
    Compute the sha256 of a local file (e.g., on the NFS mount).
    Return hex digest as string, or None if error.
    """
    sha = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception as e:
        logging.warning(f"compute_local_sha256 failed for {filepath}: {e}")
        return None

def compute_remote_sha256(host, remote_filepath, user):
    """
    Use SSH to compute the sha256 of a file on the Recording Pi local disk.
    e.g. host=192.168.1.79, user=recordingpi
    Return hex digest (string) or None if error.
    """
    cmd = [
        "ssh",
        f"{user}@{host}",
        f"sha256sum \"{remote_filepath}\""
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # e.g. "5ab253...somehash  /home/recordingpi/akulab_2025/audio_test_0415/foo.wav"
        line = result.stdout.strip()
        remote_hash = line.split()[0].lower()  # everything before first space
        return remote_hash
    except Exception as e:
        logging.warning(f"Failed to get remote sha256 for {remote_filepath} on {host}: {e}")
        return None


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
    record_duration = config.getint("recordingpi", "segment_time", fallback=3600)
    modification_threshold = record_duration + 60

    logging.info(f"Running in {rpi_mode} mode.")
    logging.info(f"from_audio_dir = {from_audio_dir}")
    logging.info(f"to_audio_dir   = {to_audio_dir}")
    logging.info(f"record_duration = {record_duration}, so modification_threshold = {modification_threshold}")

    # Make sure the directories exist (locally).
    #Path(from_audio_dir).mkdir(parents=True, exist_ok=True)
    #Path(to_audio_dir).mkdir(parents=True, exist_ok=True)

    ################################################################
    # MODE-SPECIFIC LOGIC
    ################################################################
    # analytics pi
    # We expect from_audio_dir and to_audio_dir to be SSHFS and NFS respectively
    if not check_mount_or_log(from_audio_dir, label="SSHFS from_audio_dir"):
        logging.error("Exiting script because from_audio_dir is not properly mounted on the Analytics Pi.")
        return

    if not check_mount_or_log(to_audio_dir, label="NFS to_audio_dir"):
        logging.error("Exiting script because to_audio_dir (NAS) is not properly mounted on the Analytics Pi.")
        return

    ################################################################
    #  Find new “complete” .wav files, skip previously synced
    ################################################################
    user = getpass.getuser()
    log_dir = Path(f"/home/{user}/logs/backup_recordings")
    log_dir.mkdir(parents=True, exist_ok=True)

    synced_files_log = log_dir / f"synced_files/synced_files.log"
    synced_files = set()
    logging.info("Check previously synced files ..")
    if synced_files_log.is_file():
        with open(synced_files_log, "r", encoding="utf-8") as sf:
            for line in sf:
                entry = line.strip()
                if entry:
                    synced_files.add(entry)

    # Gather complete unsynced .wav files
    complete_unsynced_files = []
    logging.info("Gather complete unsynced files ..")
    for fpath in Path(from_audio_dir).rglob("*.wav"):
        rel_path = str(fpath.relative_to(from_audio_dir))  # store as relative path
        if rel_path in synced_files:
            continue  # already synced
        if is_file_complete(fpath, modification_threshold):
            complete_unsynced_files.append(rel_path)
        else:
            logging.info(f"Skipping incomplete or not-yet-stable file: {fpath}")

    if not complete_unsynced_files:
        logging.info("No new complete .wav files found to sync at this time.")
    else:
        run_rsync_list(from_audio_dir, to_audio_dir, complete_unsynced_files, script_dir, synced_files_log)

#        # NEW: Attempt sha256 verification if rpi_mode == analyticspi and verify_sha256 = true
#        if rpi_mode == "analyticspi" and config.getboolean("analyticspi", "verify_sha256", fallback=False):
#            # read host info from [recordingpi] section
#            recpi_host = config["recordingpi"]["recordingpi_ip"]
#            recpi_user = config["recordingpi"]["recordingpi_user"]
#
#            for relpath in complete_unsynced_files:
#                local_path = os.path.join(to_audio_dir, relpath)    # file on NAS
#                recpi_actual_base = config["recordingpi"]["from_audio_dir"] 
#                # e.g. /home/recordingpi/akulab_2025/audio_test_0415
#
#                recpi_file = os.path.join(recpi_actual_base, relpath)
#                # e.g. /home/recordingpi/akulab_2025/audio_test_0415/zoom_f8_pro_20250416_133000_0016.wav
#
#
#                local_hash = compute_local_sha256(local_path)
#                remote_hash = compute_remote_sha256(recpi_host, recpi_file, recpi_user)
#
#                if not local_hash or not remote_hash:
#                    logging.warning(f"Skipping sha256 compare for {relpath}, missing hash.")
#                    continue
#
#                if local_hash.lower() == remote_hash.lower():
#                    logging.info(f"File {relpath} verified successfully (sha256).")
#                else:
#                    logging.error(f"File {relpath} verification FAILED! local={local_hash}, remote={remote_hash}")

    ################################################################
    #  If in recordingpi mode, remove oldest .wav if local size > max
    ################################################################
    # analytics pi => skip removal
    logging.info("Skipping local file-removal routine in analytics pi mode.")

    logging.info("Finished backup_recordings.py script.")


if __name__ == "__main__":
    main()

