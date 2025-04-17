#!/usr/bin/env python3

import pathlib
import argparse
import logging
import psutil
import subprocess
import time
import re
import os
import csv
from datetime import datetime
import getpass
import shlex

# --- NEW helper -----------------------------------------
def get_chrony_stats():
    """
    Returns:
      current_src  (str)  e.g. 'PPS' or '192.168.1.140'
      last_offset  (float)  seconds (+/-)
      rms_offset   (float)  seconds
      skew         (float)  ppm
    Any field that can’t be parsed is returned as None.
    """
    try:
        # 1) Which source has the * ?
        src_cmd = ["chronyc", "sources", "-n"]        # -n → numeric names
        src_out  = subprocess.run(src_cmd, capture_output=True,
                                  text=True, check=True).stdout
        current_src = None
        for line in src_out.splitlines():
            # Look for ^*  or #*  in first two chars
            if re.match(r'^[#^]\*', line):
                # field 2 is the name/ip
                current_src = line.split()[1]
                break

        # 2) Offsets & skew
        trk_cmd = ["chronyc", "tracking"]
        trk_txt = subprocess.run(trk_cmd, capture_output=True,
                                 text=True, check=True).stdout

        def grab(pattern):
            m = re.search(pattern, trk_txt)
            return float(m.group(1)) if m else None

        last_offset = grab(r"Last offset\s*:\s*([+-]?\d+\.\d+)")
        rms_offset  = grab(r"RMS offset\s*:\s*([+-]?\d+\.\d+)")
        skew        = grab(r"Skew\s*:\s*([+-]?\d+\.\d+)")

        return current_src, last_offset, rms_offset, skew

    except Exception:
        return None, None, None, None
# ----------------------------------------------------------


def get_cpu_usage():
    return psutil.cpu_percent()

def get_memory_usage():
    vm = psutil.virtual_memory()
    return vm.percent, vm.used / (1024**2), vm.available / (1024**2)

def get_temperature():
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'],
                                capture_output=True, text=True, check=True)
        temp_str = output.stdout.strip()
        match = re.search(r'temp=(\d+\.\d+)', temp_str)
        return float(match.group(1)) if match else None
    except Exception:
        return None

def get_voltage():
    try:
        output = subprocess.run(['vcgencmd', 'measure_volts', 'core'],
                                capture_output=True, text=True, check=True)
        volts_str = output.stdout.strip()
        match = re.search(r'volt=(\d+\.\d+)', volts_str)
        return float(match.group(1)) if match else None
    except Exception:
        return None

def get_network_traffic(interface="eth0"):
    try:
        prev = psutil.net_io_counters(pernic=True).get(interface)
        if not prev:
            return None, None
        time.sleep(1)
        curr = psutil.net_io_counters(pernic=True).get(interface)
        sent_kbps = (curr.bytes_sent - prev.bytes_sent) / 1024.0
        recv_kbps = (curr.bytes_recv - prev.bytes_recv) / 1024.0
        return sent_kbps, recv_kbps
    except Exception:
        return None, None

def get_disk_usage(path="/"):
    du = psutil.disk_usage(path)
    return du.percent, du.free / (1024**3)

def check_mount(mount_path):
    return os.path.ismount(mount_path)

def get_cpu_freq():
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
            return int(f.read()) / 1000.0  # MHz
    except:
        return None

def get_throttled_flags():
    try:
        result = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True)
        value = result.stdout.strip().split("=")[-1]
        return int(value, 16)  # hex to int
    except:
        return None

def is_root_fs_readonly():
    """
    Check /proc/mounts for an 'rw' entry on the root filesystem.
    Return True if root is read-only, False if it's read-write.
    """
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4 and parts[1] == "/":
                    flags = parts[3].split(",")
                    return ("rw" not in flags)
        return True  # if not found, assume read-only
    except:
        return True

def check_zoom_hw2():
    """Check if Zoom F8 Pro is enumerated as hw:2,0 by scanning arecord -l output."""
    try:
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        # e.g. look for line with 'card 2: F8' or 'card 2: ZoomF8Pro ...'
        return bool(re.search(r"card 2:.*F8", result.stdout, re.IGNORECASE))
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi health snapshot for cron.")
    parser.add_argument("--interface", type=str, default="eth0", help="Network interface (default: eth0)")
    parser.add_argument("--mount-check", nargs="*", default=[], help="Mount paths to check")
    args = parser.parse_args()

    user = getpass.getuser()
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = pathlib.Path(f"/home/{user}/logs/rpi_health_snapshot")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{today}_rpi_health.csv"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cpu = get_cpu_usage()
    mem_percent, mem_used, mem_available = get_memory_usage()
    temp = get_temperature()
    volts = get_voltage()
    sent_kbps, recv_kbps = get_network_traffic(args.interface)
    disk_percent, disk_free = get_disk_usage()
    cpu_freq = get_cpu_freq()
    throttled = get_throttled_flags()
    root_ro = is_root_fs_readonly()
    zoom_hw2_ok = check_zoom_hw2()  # new


    mount_statuses = [check_mount(m) for m in args.mount_check]

    header = [
        "timestamp",
        "cpu_percent",
        "mem_percent", "mem_used_mb", "mem_available_mb",
        "temperature_c", "voltage_v",
        f"net_sent_kbps_{args.interface}", f"net_recv_kbps_{args.interface}",
        "disk_percent", "disk_free_gb",
        "cpu_freq_mhz", "throttled_flags", "root_readonly",
        "zoom_hw2_ok"  # new column
    ] + [f"mount_ok_{p}" for p in args.mount_check]

    row = [
        now,
        cpu,
        mem_percent, mem_used, mem_available,
        temp, volts,
        sent_kbps, recv_kbps,
        disk_percent, disk_free,
        cpu_freq, throttled, root_ro,
        zoom_hw2_ok  # new
    ] + mount_statuses

    chrony_src, chrony_last, chrony_rms, chrony_skew = get_chrony_stats()

    header += ["chrony_src", "chrony_last_offset_s",
               "chrony_rms_offset_s", "chrony_freq_skew_ppm"]
    row    += [chrony_src, chrony_last, chrony_rms, chrony_skew]

    write_header = not os.path.exists(log_path)
    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)
        writer.writerow(row)

if __name__ == "__main__":
    main()

