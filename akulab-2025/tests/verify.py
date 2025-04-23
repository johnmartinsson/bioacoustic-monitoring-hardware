import os
import sys
from datetime import datetime, timedelta
import statistics

def parse_ls_output(file_path):
    """Parse the ls -al output to extract filenames and their sizes."""
    file_sizes = {}
    filenames = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) < 9:
                continue  # Skip lines that don't have enough parts
            size = int(parts[4])  # File size is the 5th column
            filename = ' '.join(parts[8:])  # Filename starts from the 9th column
            file_sizes[filename] = size
            filenames.append(filename)
    return file_sizes, sorted(set(filenames))  # Return file sizes and sorted filenames

def check_consecutive_segments(audio_files):
    """Check if all 10-minute segments are consecutive and identify missing ones."""
    timestamps = []

    # Extract timestamps from file names (assuming format: YYYYMMDD_HHMMSS)
    for file in audio_files:
        try:
            timestamp_str = file.split('_')[-2]  # Extract HHMMSS part from the second-to-last segment
            timestamp = datetime.strptime(timestamp_str, "%H%M%S")
            # Validate that the timestamp is aligned to a 10-minute boundary
            if timestamp.minute % 10 != 0 or timestamp.second != 0:
                print(f"Invalid timestamp (not aligned to 10-minute boundary): {file}")
                continue
            timestamps.append(timestamp)
        except ValueError:
            print(f"Invalid timestamp format in file: {file}")

    # Sort timestamps
    timestamps.sort()

    # Check for gaps
    missing_segments = []
    for i in range(len(timestamps) - 1):
        expected_next = timestamps[i] + timedelta(minutes=10)
        if timestamps[i + 1] != expected_next:
            current = timestamps[i]
            while current + timedelta(minutes=10) < timestamps[i + 1]:
                current += timedelta(minutes=10)
                missing_segments.append(current.strftime("%H:%M"))

    if missing_segments:
        print("Missing 10-minute segments:")
        for segment in missing_segments:
            print(f"  {segment}")
    else:
        print("All 10-minute segments are consecutive.")

def analyze_file_sizes(file_sizes):
    """Analyze file sizes and identify files far from the mean."""
    sizes = list(file_sizes.values())
    if not sizes:
        print("No files to analyze.")
        return

    mean_size = statistics.mean(sizes)
    std_dev = statistics.stdev(sizes) if len(sizes) > 1 else 0

    print(f"Mean file size: {mean_size:.2f} bytes")
    print(f"Standard deviation: {std_dev:.2f} bytes")

    threshold = 2 * std_dev  # Define a threshold for "far from the mean"
    outliers = {filename: size for filename, size in file_sizes.items() if abs(size - mean_size) > threshold}

    if outliers:
        print("\nFiles with sizes far from the mean:")
        for filename, size in outliers.items():
            print(f"  {filename}: {size} bytes")
    else:
        print("\nNo files with sizes far from the mean.")

# Example usage in main()
def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else 'ls_output.txt'

    file_sizes, audio_files = parse_ls_output(file_path)
    print(f"Parsed {len(audio_files)} unique audio files.")

    print("\nAnalyzing file sizes...")
    analyze_file_sizes(file_sizes)

    print("\nChecking consecutive 10-minute segments...")
    check_consecutive_segments(audio_files)
    #for file in audio_files:
    #    print(f"file:  {file}")
    print("All audio files processed.")

if __name__ == "__main__":
    main()