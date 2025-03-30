#!/usr/bin/env python3

import argparse
import logging
import psutil
import subprocess
import time
import re
import os


def get_cpu_usage():
    """Returns CPU usage as a percentage."""
    return psutil.cpu_percent()


def get_memory_usage():
    """Returns memory usage details in MB."""
    vm = psutil.virtual_memory()
    return {
        'total': vm.total / (1024**2),
        'available': vm.available / (1024**2),
        'used': vm.used / (1024**2),
        'percent': vm.percent
    }


def get_temperature():
    """Returns CPU temperature in Celsius using vcgencmd."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'],
                                capture_output=True,
                                text=True,
                                check=True)
        temp_str = output.stdout.strip()
        match = re.search(r'temp=(\d+\.\d+)', temp_str)
        if match:
            return float(match.group(1))
        else:
            return None  # Temperature not found in output
    except (subprocess.CalledProcessError, FileNotFoundError):
        # vcgencmd not available or command failed
        return None


def get_voltage():
    """Returns core voltage using vcgencmd."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_volts', 'core'],
                                capture_output=True,
                                text=True,
                                check=True)
        volts_str = output.stdout.strip()
        match = re.search(r'volt=(\d+\.\d+)', volts_str)
        if match:
            return float(match.group(1))
        else:
            return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_network_traffic(interface="eth0"):
    """
    Returns network traffic in KB/s for a given interface.
    Resets counters each call, so call once per sample interval.
    """
    try:
        prev_counters = psutil.net_io_counters(pernic=True).get(interface)
        if not prev_counters:
            return None  # Interface not found
        time.sleep(1)  # Wait for 1 second to get a delta
        curr_counters = psutil.net_io_counters(pernic=True).get(interface)
        if not curr_counters:
            return None  # Interface disappeared

        bytes_sent = curr_counters.bytes_sent - prev_counters.bytes_sent
        bytes_recv = curr_counters.bytes_recv - prev_counters.bytes_recv
        return {
            'sent_kbps': bytes_sent / 1024.0,  # KB/s
            'recv_kbps': bytes_recv / 1024.0
        }
    except Exception as e:
        logging.error(f"Error getting network traffic: {e}")
        return None


def get_disk_usage(path="/"):
    """Returns disk usage for a given path (default: root), in GB."""
    du = psutil.disk_usage(path)
    return {
        'total': du.total / (1024**3),
        'used': du.used / (1024**3),
        'free': du.free / (1024**3),
        'percent': du.percent
    }


def check_mount(mount_path):
    """
    Simple check to see if mount_path is actually mounted.
    Returns True if mounted; False otherwise.
    """
    if not os.path.ismount(mount_path):
        logging.warning(f"Mount check FAILED: {mount_path} is not mounted.")
        return False
    else:
        logging.info(f"Mount check OK: {mount_path} is mounted.")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Raspberry Pi health monitoring script."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Sampling interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--interface",
        type=str,
        default="eth0",
        help="Network interface to monitor (default: eth0)"
    )
    parser.add_argument(
        "--mount-check",
        type=str,
        nargs="*",
        default=[],
        help="Optional mount paths to check. Example: /mnt/usb /mnt/sshfs"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="rpi_health.log",
        help="Log file path (default: rpi_health.log)"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        filename=args.log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logging.info("Starting rpi_health_monitor.py with interval=%ds", args.interval)

    while True:
        cpu_percent = get_cpu_usage()
        mem_usage = get_memory_usage()
        temp_celsius = get_temperature()
        voltage_core = get_voltage()
        net_traffic = get_network_traffic(args.interface)
        disk_usage_root = get_disk_usage("/")
        # Optionally check additional mount paths
        for path in args.mount_check:
            check_mount(path)

        # Log output
        logging.info("----- Health Report -----")
        if cpu_percent is not None:
            logging.info(f"CPU Usage: {cpu_percent:.1f}%%")
        else:
            logging.warning("CPU Usage: N/A")

        if mem_usage:
            logging.info(f"Memory Usage: {mem_usage['percent']:.1f}%% "
                         f"(Used: {mem_usage['used']:.1f} MB, "
                         f"Avail: {mem_usage['available']:.1f} MB)")
        else:
            logging.warning("Memory Usage: N/A")

        if temp_celsius is not None:
            logging.info(f"CPU Temperature: {temp_celsius:.1f}°C")
            # Check for high temperature
            if temp_celsius > 70.0:
                logging.warning("CPU Temperature is above 70°C!")
        else:
            logging.warning("Temperature: N/A")

        if voltage_core is not None:
            logging.info(f"Core Voltage: {voltage_core:.2f}V")
        else:
            logging.warning("Core Voltage: N/A")

        if net_traffic:
            logging.info(f"Network Traffic ({args.interface}): "
                         f"Sent={net_traffic['sent_kbps']:.1f} KB/s, "
                         f"Recv={net_traffic['recv_kbps']:.1f} KB/s")
        else:
            logging.warning(f"Network Traffic ({args.interface}): N/A")

        if disk_usage_root:
            logging.info(f"Disk Usage (/): {disk_usage_root['percent']:.1f}%% used "
                         f"(Free: {disk_usage_root['free']:.2f} GB)")
            # Example alert if free < 2 GB
            if disk_usage_root['free'] < 2.0:
                logging.warning("Root file system free space < 2 GB!")
        else:
            logging.warning("Disk Usage (/): N/A")

        logging.info("-------------------------\n")

        # Sleep until next interval
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
