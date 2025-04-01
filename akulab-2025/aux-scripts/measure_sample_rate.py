#!/usr/bin/env python3

import argparse
import datetime
import time
import subprocess
import wave
import os

def wait_until(target_time):
    """
    Sleep until the system clock reaches the specified 'target_time' (a datetime).
    """
    now = datetime.datetime.now()
    if now >= target_time:
        print(f"WARNING: target_time {target_time} is in the past. Proceeding immediately.")
        return
    wait_seconds = (target_time - now).total_seconds()
    print(f"Waiting {wait_seconds:.1f} seconds until {target_time}...")
    time.sleep(wait_seconds)

def record_audio_ffmpeg(device, out_wav, duration, samplerate, channels):
    """
    Run FFmpeg to capture audio from the ALSA device for the specified duration.
    - device: e.g. 'hw:2,0'
    - out_wav: output file path
    - duration: in seconds
    - samplerate: nominal sample rate for capturing
    - channels: number of channels
    """
    # Construct the ffmpeg command line
    # Using 32-bit float (pcm_f32le), but you can change to s16le or s24le if desired
    # Also note: -ar in FFmpeg does not "resample" here, it just sets the nominal rate for capture
    cmd = [
        "ffmpeg",
        "-y",                  # overwrite existing file
        "-hide_banner",
        "-loglevel", "warning",
        "-f", "alsa",
        "-channels", str(channels),
        "-sample_rate", str(samplerate),
        "-i", device,
        "-t", str(duration),
        "-c:a", "pcm_f32le",   # raw float WAV
        out_wav
    ]

    print("Running FFmpeg command:")
    print(" ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError("FFmpeg recording failed. Check device name/permissions.")

def get_num_frames(wav_path):
    """
    Use Python's wave module to read total frames in a WAV file.
    """
    with wave.open(wav_path, 'rb') as wf:
        frames = wf.getnframes()
        return frames, wf.getframerate(), wf.getnchannels()

def main():
    parser = argparse.ArgumentParser(
        description="Record from an ALSA device for a fixed time at a specific start, then compute actual sample rate."
    )
    parser.add_argument("--device", default="hw:2,0",
                        help="ALSA device name (default: hw:2,0).")
    parser.add_argument("--start-time", type=str, required=True,
                        help="Local date/time to start recording (YYYY-MM-DD HH:MM:SS). Example: 2025-04-02 10:00:00")
    parser.add_argument("--duration", type=int, default=600,
                        help="Number of seconds to record (default: 600).")
    parser.add_argument("--samplerate", type=int, default=48000,
                        help="Nominal sample rate used by FFmpeg (default: 48000).")
    parser.add_argument("--channels", type=int, default=2,
                        help="Number of input channels (default: 2).")
    parser.add_argument("--outfile", default="test.wav",
                        help="Output WAV file name (default: test.wav).")

    args = parser.parse_args()

    # Parse the user-supplied start time
    try:
        start_dt = datetime.datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("ERROR: start-time must be in format YYYY-MM-DD HH:MM:SS")
        return

    # 1) Wait until target start time
    wait_until(start_dt)

    # 2) Record for specified duration
    record_audio_ffmpeg(
        device=args.device,
        out_wav=args.outfile,
        duration=args.duration,
        samplerate=args.samplerate,
        channels=args.channels
    )

    # 3) Count frames in resulting WAV
    frames, wave_sr, wave_ch = get_num_frames(args.outfile)

    # 4) Compute actual sample rate based on known real-time duration
    #    We assume the system clock was accurate about the start/stop time => total = args.duration seconds
    #    (If you want to measure EXACT start/stop in real time, you can do your own timing around the ffmpeg call.)
    actual_sr = frames / args.duration

    # 5) Print results
    print("\n===== Recording Summary =====")
    print(f"Nominal samplerate requested  : {args.samplerate} Hz")
    print(f"WAV file samplerate (header)  : {wave_sr} Hz")
    print(f"Total frames captured         : {frames}")
    print(f"Recording duration (seconds)  : {args.duration}")
    print(f"Computed actual sample rate   : {actual_sr:.2f} Hz")
    print(f"Difference from nominal       : {actual_sr - args.samplerate:.2f} Hz\n")
    print("Done.")

if __name__ == "__main__":
    main()
