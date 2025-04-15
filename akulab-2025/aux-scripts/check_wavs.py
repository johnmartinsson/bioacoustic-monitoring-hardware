#!/usr/bin/env python3

import os
import sys
import soundfile as sf

def main(directory):
    total_frames = 0
    valid_files = 0

    for filename in os.listdir(directory):
        if filename.lower().endswith(".wav"):
            filepath = os.path.join(directory, filename)
            try:
                with sf.SoundFile(filepath) as snd:
                    # Check number of channels
                    if snd.channels != 8:
                        print(f"{filename}: not 8 channels; skipping.")
                        continue
                    # Check format is 32-bit float
                    # SoundFile uses 'FLOAT' as the subtype for 32-bit float WAV
                    if snd.subtype != 'FLOAT':
                        print(f"{filename}: not 32-bit float (found {snd.subtype}); skipping.")
                        continue

                    frames = len(snd)  # total audio frames
                    total_frames += frames
                    valid_files += 1

            except RuntimeError as e:
                print(f"{filename}: error reading file: {e}")

    if valid_files == 0:
        print("No valid 8-channel, 32-bit float WAV files found.")
        return

    # Each valid file is assumed to be 1 hour = 3600 seconds
    average_sample_rate = total_frames / (valid_files * 3600.0)
    print(f"Found {valid_files} valid 8-ch 32-bit float WAV files.")
    print(f"Average sample rate = {average_sample_rate:.2f} Hz")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <directory_of_wav_files>")
        sys.exit(1)

    main(sys.argv[1])

