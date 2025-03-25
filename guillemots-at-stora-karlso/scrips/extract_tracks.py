import soundfile as sf
import argparse
import os

def extract_tracks(input_wav_file, track_indices, output_base_name):
    """
    Extracts specified tracks from a multi-track WAV file and saves them
    as separate single-track WAV files.

    Args:
        input_wav_file (str): Path to the input multi-track WAV file.
        track_indices (list): List of track indices to extract (1-based indexing).
        output_base_name (str): Base name for output files (e.g., 'recording_name').
    """
    try:
        # Read the multi-track WAV file
        data, samplerate = sf.read(input_wav_file)

        # Check if it's actually multi-channel (more than one track)
        if data.ndim < 2:
            print(f"Error: Input file '{input_wav_file}' does not appear to be multi-track.")
            return

        num_channels = data.shape[1] # Get the number of channels (tracks)
        print(f"Input file has {num_channels} tracks.")

        for track_number in track_indices:
            if track_number <= 0 or track_number > num_channels:
                print(f"Error: Track {track_number} is out of range (1 to {num_channels}). Skipping track {track_number}.")
                continue

            track_index_0based = track_number - 1  # Convert to 0-based indexing
            track_data = data[:, track_index_0based]
            output_file = f"{output_base_name}_track_{track_number}.wav"
            sf.write(output_file, track_data, samplerate, subtype='FLOAT')
            print(f"Track {track_number} saved to '{output_file}'")

        print("Track extraction complete.")

    except sf.LibsndfileError as e:
        print(f"Error reading or writing WAV file: {e}")
    except FileNotFoundError:
        print(f"Error: Input file '{input_wav_file}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract tracks from a multi-track WAV file.")
    parser.add_argument("input_file", help="Path to the input multi-track WAV file.")
    parser.add_argument("tracks", help="Comma-separated list of track numbers to extract (e.g., '2,5').")

    args = parser.parse_args()

    input_file = args.input_file
    tracks_str = args.tracks

    try:
        track_indices = [int(track.strip()) for track in tracks_str.split(',')]
    except ValueError:
        print("Error: Invalid track numbers. Please provide a comma-separated list of integers (e.g., '2,5').")
        exit(1)

    if not track_indices:
        print("Error: No track numbers specified.")
        exit(1)

    # Create output base name from input file name (remove extension)
    output_base_name = os.path.splitext(os.path.basename(input_file))[0]

    extract_tracks(input_file, track_indices, output_base_name)
