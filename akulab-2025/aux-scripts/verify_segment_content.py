#!/usr/bin/env python3

"""
verify_spectrogram_and_continuity.py

1) For each .wav in a directory, generate an 8-row spectrogram figure (one row per channel).
   Save as "<basename>_spectrogram.png".

2) For consecutive .wav files (sorted by name), verify continuity by:
   - Reading a short region at the end of the first file
   - Reading a short region at the start of the second file
   - Plotting them (time domain waveforms) in 8 stacked subplots
   - Mark a dashed vertical line at the boundary
   - Save as "<basename1>_TO_<basename2>_waveform_continuous.png"

Assumes 8-ch, float, 48 kHz, but it should adapt to actual # channels.
"""

import os
import sys
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt

# How many seconds to capture at the end of the file
TAIL_SECONDS = 0.01  # adjust as you like
# How many seconds to capture at the beginning of the file
HEAD_SECONDS = 0.01  # adjust as you like


def plot_spectrograms(wavpath, out_png):
    """
    Read entire file, produce 8 subplots (one per channel) of spectrogram, and save.
    """
    data, sr = sf.read(wavpath)  # shape: (frames, channels)
    # data shape => (samples, channels)

    if data.ndim == 1:
        # only 1 channel
        data = data[:, np.newaxis]
    channels = data.shape[1]

    fig, axes = plt.subplots(channels, 1, figsize=(10, 2*channels), sharex=True)
    if channels == 1:
        axes = [axes]  # make it iterable

    for ch in range(channels):
        ax = axes[ch]
        ax.specgram(data[:, ch], Fs=sr, cmap='viridis')
        ax.set_ylabel(f"Ch{ch+1}")
        if ch == 0:
            ax.set_title(os.path.basename(wavpath))
        if ch == channels - 1:
            ax.set_xlabel("Time (s)")

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close(fig)


def plot_boundary_continuity(wav1, wav2, out_png, tail_sec=0.1, head_sec=0.1):
    """
    Read the last tail_sec from wav1 and first head_sec from wav2,
    then plot waveforms for all channels stacked, with a dashed line
    at the boundary. Save figure to out_png.
    """
    info1 = sf.info(wav1)
    info2 = sf.info(wav2)

    sr1, sr2 = info1.samplerate, info2.samplerate
    if sr1 != sr2:
        print(f"WARNING: sample rates differ for {wav1} ({sr1}) vs {wav2} ({sr2}).")
        # We'll just proceed, but you'd typically handle this more gracefully.

    sr = sr1  # assume they match

    frames1 = info1.frames
    frames_tail = int(tail_sec * sr)
    frames_head = int(head_sec * sr)

    # Make sure we don't go negative
    start_tail = max(0, frames1 - frames_tail)

    data_tail, _ = sf.read(wav1, start=start_tail, frames=frames_tail, dtype='float32')
    data_head, _ = sf.read(wav2, start=0, frames=frames_head, dtype='float32')

    # If either is 1D, reshape
    if data_tail.ndim == 1:
        data_tail = data_tail[:, np.newaxis]
    if data_head.ndim == 1:
        data_head = data_head[:, np.newaxis]

    # For simpler code, ensure same #channels
    if data_tail.shape[1] != data_head.shape[1]:
        print(f"ERROR: channel mismatch {data_tail.shape[1]} vs {data_head.shape[1]}")
        return

    channels = data_tail.shape[1]

    # Concatenate along time axis
    combined = np.concatenate((data_tail, data_head), axis=0)

    # Time vector for combined data
    total_frames = combined.shape[0]
    time = np.linspace(0, total_frames / sr, total_frames, endpoint=False)
    boundary_time = data_tail.shape[0] / sr  # where the tail ends

    # Plot waveforms
    fig, axes = plt.subplots(channels, 1, figsize=(10, 2*channels), sharex=True)
    if channels == 1:
        axes = [axes]

    for ch in range(channels):
        ax = axes[ch]
        ax.plot(time, combined[:, ch], label=f"Ch{ch+1}")
        ax.axvline(x=boundary_time, color='r', ls='--', label='Segment boundary')
        if ch == 0:
            ax.set_title(f"{os.path.basename(wav1)} -> {os.path.basename(wav2)}")
        if ch == channels - 1:
            ax.set_xlabel("Time (s)")
        ax.set_ylabel(f"Ch{ch+1}")

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        print("Usage: verify_spectrogram_and_continuity.py <directory_of_wav_files>")
        sys.exit(1)

    directory = sys.argv[1]
    # Gather all WAV files
    wavs = [f for f in os.listdir(directory) if f.lower().endswith('.wav')]
    if not wavs:
        print("No .wav files found.")
        return

    # Sort by name (assuming the date-based filenames already sort chronologically)
    wavs.sort()
    wavpaths = [os.path.join(directory, w) for w in wavs]

    # 1) Create spectrogram for each
    #for wp in wavpaths:
    #    out_png = wp.rsplit('.', 1)[0] + "_spectrogram.png"
    #    print(f"Creating spectrogram for {wp}")
    #    plot_spectrograms(wp, out_png)

    # 2) Create continuity plots between consecutive pairs
    for i in range(len(wavpaths) - 1):
        wp1 = wavpaths[i]
        wp2 = wavpaths[i+1]
        # e.g. "zoom_audio_20250414_113100_TO_zoom_audio_20250414_113200_waveform_continuous.png"
        out_png = (wp1.rsplit('.', 1)[0] + 
                   "_TO_" + 
                   os.path.basename(wp2).rsplit('.',1)[0] + 
                   "_waveform_continuous.png")
        out_png = out_png.replace('/', '_')  # just in case, remove extra path separators
        out_png = os.path.join(directory, os.path.basename(out_png))
        print(f"Checking boundary continuity between {wp1} and {wp2}")
        plot_boundary_continuity(wp1, wp2, out_png, 
                                 tail_sec=TAIL_SECONDS, 
                                 head_sec=HEAD_SECONDS)


if __name__ == "__main__":
    main()

