import os
import time
import datetime
import logging

# Configuration
ZOOM_STORAGE_DIRECTORY = "simulated_zoom_storage"
RECORDING_CHUNK_INTERVAL = 10  # seconds (simulating 1-minute recording chunks)
SDCARD_MOUNT_POINT = "simulated_zoom_sdcard" # Simulate SD card mount point

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Zoom F8 Pro - %(levelname)s - %(message)s')

def create_dummy_audio_file():
    """Creates a dummy audio file to simulate recording."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"audio_chunk_{timestamp}.wav" # Simulate Zoom's filename convention
    filepath = os.path.join(SDCARD_MOUNT_POINT, ZOOM_STORAGE_DIRECTORY, filename)

    # Create an empty file (or you could write some dummy data)
    open(filepath, 'w').close() # creates an empty file

    logging.info(f"Created dummy audio file: {filename}")
    return filename

def simulate_recording():
    """Simulates recording audio in chunks."""
    logging.info(f"Zoom F8 Pro recording simulation started. Storing in: {os.path.join(SDCARD_MOUNT_POINT, ZOOM_STORAGE_DIRECTORY)}")
    while True:
        create_dummy_audio_file()
        time.sleep(RECORDING_CHUNK_INTERVAL)

if __name__ == "__main__":
    os.makedirs(os.path.join(SDCARD_MOUNT_POINT, ZOOM_STORAGE_DIRECTORY), exist_ok=True) # Simulate SD card directory structure
    simulate_recording()