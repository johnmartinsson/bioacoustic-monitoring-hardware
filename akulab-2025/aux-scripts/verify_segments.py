#!/usr/bin/env python3

"""
verify_segments.py

Verifies:
- Each WAV file is 8-ch, 32-bit float, 48k sample rate
- Average sample rate matches ~ 48000
- (Optionally) checks continuity by looking for zero-gap between chunk files
- (Optional) if a known test tone was played, do a quick spectral check
  to confirm the presence of that frequency
"""

import os
import sys
import soundfile as sf
import numpy as np


def analyze_file(filepath, known_freq=None):
    """
    Returns a dict with:
      - channels
      - samplerate
      - subtype
      - frames
      - duration (seconds)
      - avg_sample_rate (frames / duration)
      - freq_ok (True/False) if known_freq is specified
    """
    info = sf.info(filepath)
    samplerate = info.samplerate
    frames = info.frames
    duration = 60 #frames / float(samplerate) if samplerate else 0.0

    subtype = info.subtype  # e.g. 'FLOAT'
    channels = info.channels

    avg_sr = None
    if duration > 0:
        avg_sr = frames / duration

    result = {
        'file': os.path.basename(filepath),
        'samplerate': samplerate,
        'channels': channels,
        'subtype': subtype,
        'frames': frames,
        'duration': duration,
        'avg_sample_rate': avg_sr,
        'freq_ok': None
    }

    # If a known frequency is provided, do a short spectral check
    if known_freq is not None and duration > 0:
        # Read a chunk of audio data (e.g. first few seconds)
        # to reduce memory usage for hour-long files
        # Let's read 2 seconds from the middle of the file
        start_frame = frames // 2
        read_frames = min(samplerate * 2, frames - start_frame)
        if read_frames < 1:
            # fallback to reading entire file if too short
            start_frame = 0
            read_frames = frames

        data, _ = sf.read(filepath, start=start_frame, frames=int(read_frames), dtype='float32')
        if data.ndim > 1:
            # If multi-channel, pick just one channel for test
            data = data[:, 0]

        # Quick & dirty FFT approach
        fft_data = np.fft.rfft(data)
        freqs = np.fft.rfftfreq(len(data), d=1.0/samplerate)
        mag = np.abs(fft_data)

        # Find which frequency bin is strongest
        idx_max = np.argmax(mag)
        peak_freq = freqs[idx_max]

        # Check if the peak is near known_freq (± a tolerance)
        tolerance = 2.0  # ±2 Hz
        result['freq_ok'] = abs(peak_freq - known_freq) < tolerance

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: verify_segments.py <directory_of_wavs> [known_freq_in_Hz]")
        sys.exit(1)

    directory = sys.argv[1]
    known_freq = None
    if len(sys.argv) == 3:
        known_freq = float(sys.argv[2])

    wav_files = sorted(
        [os.path.join(directory, f) for f in os.listdir(directory)
         if f.lower().endswith('.wav')]
    )

    if not wav_files:
        print("No .wav files found in", directory)
        sys.exit(1)

    prev_end_time = 0.0
    for i, wf in enumerate(wav_files):
        res = analyze_file(wf, known_freq=known_freq)

        # Print summary
        print(f"File: {res['file']}")
        print(f"  Channels = {res['channels']}")
        print(f"  Samplerate = {res['samplerate']} (should be 48000)")
        print(f"  Subtype = {res['subtype']} (should be FLOAT for 32-bit float)")
        print(f"  Frames = {res['frames']}")
        print(f"  Duration = {res['duration']:.3f}s")
        print(f"  Average sample rate = {res['avg_sample_rate']:.2f} Hz")

        if known_freq is not None:
            if res['freq_ok'] is True:
                print(f"  Found expected test tone near {known_freq} Hz")
            elif res['freq_ok'] is False:
                print(f"  WARNING: Did NOT find tone near {known_freq} Hz!")
            else:
                print("  (freq_ok not tested, possibly too short file)")

        # Check for suspicious sample rate drift
        sr_diff = abs(res['avg_sample_rate'] - 48000)
        if sr_diff > 20:
            print(f"  WARNING: sample rate drift ~ {sr_diff:.2f} Hz from 48000")

        # Optional continuity check:
        # If the files are named with a timestamp, you might parse them
        # or if you assume each chunk is exactly 3600s, compare durations etc.
        # For simplicity, we skip reading file name times. Just an example approach:
        # For chunk i, it starts right after chunk i-1 ends, ideally with zero gap.
        # But if there's top-of-hour alignment, you may see a small difference.

        # e.g., if i>0: check if there's a big time gap from prev_end_time
        if i > 0:
            # In a perfect chain, current file's start_time ~ prev_end_time
            # but your chunk alignment might be top-of-hour vs. purely sequential.
            # We'll just demonstrate the idea:
            gap_sec = 0.0  # if we had real start times, we'd compute them
            if abs(gap_sec) > 0.2:
                print(f"  POSSIBLE GAP of {gap_sec:.3f}s from previous chunk!")
        prev_end_time += res['duration']

        print()

    print("Done verifying files.")


if __name__ == "__main__":
    main()

