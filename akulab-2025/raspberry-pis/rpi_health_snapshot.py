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


def get_cpu_usage():
    return psutil.cpu_percent()


def get_memory_usage():
    vm = psutil.virtual_memory()
    return vm.percent, vm.used / (1024**2), vm.available / (1024**2)


def get_temperature():
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'],
                                capture_output=True,
                                text=True,
                                check=True)
        temp_str = output.stdout.strip()
        match = re.search(r'temp=(\d+\.\d+)', temp_str)
        return float(match.group(1)) if match else None
    except Exception:
        return None


def get_voltage():
    try:
        output = subprocess.run(['vcgencmd', 'measure_volts', 'core'],
                                capture_output=True,
                                text=True,
                                check=True)
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


def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi health snapshot for cron.")

    # Default to same directory as script
    default_csv_path = pathlib.Path(__file__).resolve().parent / "rpi_health.csv"

    parser.add_argument("--interface", type=str, default="eth0", help="Network interface (default: eth0)")
    parser.add_argument("--mount-check", nargs="*", default=[], help="Mount paths to check")
    parser.add_argument("--csv", type=str, default=str(default_csv_path), help="Path to CSV output")
    args = parser.parse_args()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Gather metrics
    cpu = get_cpu_usage()
    mem_percent, mem_used, mem_available = get_memory_usage()
    temp = get_temperature()
    volts = get_voltage()
    sent_kbps, recv_kbps = get_network_traffic(args.interface)
    disk_percent, disk_free = get_disk_usage()

    mount_statuses = [check_mount(m) for m in args.mount_check]

    # Header
    header = [
        "timestamp",
        "cpu_percent",
        "mem_percent", "mem_used_mb", "mem_available_mb",
        "temperature_c", "voltage_v",
        f"net_sent_kbps_{args.interface}", f"net_recv_kbps_{args.interface}",
        "disk_percent", "disk_free_gb"
    ] + [f"mount_ok_{p}" for p in args.mount_check]

    row = [
        now,
        cpu,
        mem_percent, mem_used, mem_available,
        temp, volts,
        sent_kbps, recv_kbps,
        disk_percent, disk_free
    ] + mount_statuses

    # Write to CSV
    write_header = not os.path.exists(args.csv)
    with open(args.csv, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)
        writer.writerow(row)


if __name__ == "__main__":
    main()
