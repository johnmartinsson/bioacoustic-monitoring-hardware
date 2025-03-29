import psutil
import subprocess
import time
import re

def get_cpu_usage():
    """Returns CPU usage as a percentage."""
    return psutil.cpu_percent()

def get_memory_usage():
    """Returns memory usage details."""
    vm = psutil.virtual_memory()
    return {
        'total': vm.total / (1024**2),  # in MB
        'available': vm.available / (1024**2),  # in MB
        'used': vm.used / (1024**2),  # in MB
        'percent': vm.percent
    }

def get_temperature():
    """Returns CPU temperature in Celsius using vcgencmd."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, check=True)
        temp_str = output.stdout.strip()
        # Extract temperature value using regex
        match = re.search(r'temp=(\d+\.\d+)', temp_str)
        if match:
            return float(match.group(1))
        else:
            return None  # Temperature not found in output
    except subprocess.CalledProcessError:
        return None  # vcgencmd command failed
    except FileNotFoundError:
        return None # vcgencmd not found (not on Raspberry Pi?)

def get_voltage():
    """Returns core voltage using vcgencmd."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_volts', 'core'], capture_output=True, text=True, check=True)
        volts_str = output.stdout.strip()
        # Extract voltage value using regex
        match = re.search(r'volt=(\d+\.\d+)', volts_str)
        if match:
            return float(match.group(1))
        else:
            return None # Voltage not found
    except subprocess.CalledProcessError:
        return None  # vcgencmd command failed
    except FileNotFoundError:
        return None # vcgencmd not found (not on Raspberry Pi?)

def get_network_traffic(interface="eth0"):
    """Returns network traffic in KB/s for a given interface."""
    try:
        prev_counters = psutil.net_io_counters(pernic=True).get(interface)
        if not prev_counters:
            return None # Interface not found
        time.sleep(1) # Wait for 1 second to calculate rate
        curr_counters = psutil.net_io_counters(pernic=True).get(interface)
        if not curr_counters:
            return None # Interface disappeared?

        bytes_sent = curr_counters.bytes_sent - prev_counters.bytes_sent
        bytes_recv = curr_counters.bytes_recv - prev_counters.bytes_recv

        return {
            'sent_kbps': (bytes_sent / 1024) , # KB/s
            'recv_kbps': (bytes_recv / 1024) # KB/s
        }
    except Exception as e:
        print(f"Error getting network traffic: {e}")
        return None

def get_disk_usage(path="/"):
    """Returns disk usage for a given path (default: root)."""
    du = psutil.disk_usage(path)
    return {
        'total': du.total / (1024**3),  # in GB
        'used': du.used / (1024**3),  # in GB
        'free': du.free / (1024**3),  # in GB
        'percent': du.percent
    }

def main():
    interface_name = "eth0" # Change this if your ethernet interface is different (e.g., wlan0 for WiFi)
    while True:
        print("---------------------")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        cpu_percent = get_cpu_usage()
        if cpu_percent is not None:
            print(f"CPU Usage: {cpu_percent}%")
        else:
            print("CPU Usage: N/A")

        mem_usage = get_memory_usage()
        if mem_usage:
            print("Memory Usage:")
            print(f"  Total: {mem_usage['total']:.2f} MB")
            print(f"  Used: {mem_usage['used']:.2f} MB")
            print(f"  Available: {mem_usage['available']:.2f} MB")
            print(f"  Percent: {mem_usage['percent']}%")
        else:
            print("Memory Usage: N/A")

        temp_celsius = get_temperature()
        if temp_celsius is not None:
            print(f"Temperature: {temp_celsius:.2f}°C")
        else:
            print("Temperature: N/A")

        voltage_core = get_voltage()
        if voltage_core is not None:
            print(f"Core Voltage: {voltage_core:.2f}V")
        else:
            print("Core Voltage: N/A")

        net_traffic = get_network_traffic(interface_name)
        if net_traffic:
            print(f"Network Traffic ({interface_name}):")
            print(f"  Sent: {net_traffic['sent_kbps']:.2f} KB/s")
            print(f"  Received: {net_traffic['recv_kbps']:.2f} KB/s")
        else:
            print(f"Network Traffic ({interface_name}): N/A")

        disk_usage = get_disk_usage()
        if disk_usage:
            print("Disk Usage (/):")
            print(f"  Total: {disk_usage['total']:.2f} GB")
            print(f"  Used: {disk_usage['used']:.2f} GB")
            print(f"  Free: {disk_usage['free']:.2f} GB")
            print(f"  Percent: {disk_usage['percent']}%")
        else:
            print("Disk Usage (/): N/A")


        time.sleep(5) # Check every 5 seconds

if __name__ == "__main__":
    main()
