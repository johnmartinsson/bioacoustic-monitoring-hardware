# Reference: `ffmpeg` Audio Recording & Timestamping for A/V Sync (Zoom F3/Ubuntu)

This document summarizes key learnings and techniques for long-term audio recording using a Zoom F3 as a USB audio interface with `ffmpeg` on Ubuntu, focusing on achieving precise timestamping for synchronization with a separate video stream.

## 1. Device Connection & Initial Setup (Zoom F3)

*   **REC/HOLD Switch:** Must **NOT** be in the "HOLD" position to power on or operate the F3. This is a common cause for the device appearing "dead."
*   **USB Audio Interface Mode (F3):**
    *   Navigate on F3: `MENU > USB Audio I/F > PC/Mac`.
    *   Select `Float` for 32-bit float audio stream or `Linear` for 24-bit.
    *   **Note:** The F3 **cannot** use its UltraSync BLUE timecode input feature while it is in USB Audio Interface mode.
*   **Power Stability:**
    *   Crucial for audio interface mode. If the F3 shuts down unexpectedly when switching to or starting in this mode, it almost always indicates insufficient USB power.
    *   **Troubleshooting:**
        *   Connect the laptop to AC power.
        *   Use a high-quality USB cable known for data transfer (not charge-only).
        *   Connect the F3 directly to a USB port on the laptop (avoid unpowered hubs).
        *   Consider having fresh AA batteries installed in the F3 as a power buffer, even when USB connected.

## 2. Identifying Audio Device in Linux (Ubuntu)

Open a terminal to use these commands:

*   **`lsusb`**: Confirms basic USB connection and lists Vendor/Product IDs. Look for "Zoom Corporation".
*   **`aplay -l`** / **`arecord -l`**: Lists ALSA playback/capture devices. Identifies the F3's card number and device number (e.g., `card 2: F3 ... device 0`), which translates to an ALSA device name like `hw:2,0`.
*   **`pactl list short sources`**: Lists PulseAudio/PipeWire manageable recording sources. This provides a user-friendly name (e.g., `alsa_input.usb-ZOOM_Corporation_F3-00.analog-stereo`) which is **generally preferred for `ffmpeg` input** on modern desktop systems.
*   **`cat /proc/asound/cardX/stream0`**: (Replace `X` with the card number). Shows raw ALSA capabilities of the device, including supported formats (e.g., `FLOAT_LE` for 32-bit float), sample rates, and channels.

## 3. `ffmpeg` for Recording

*   **Direct ALSA Input (`-f alsa -i hw:X,Y`):**
    *   Can be less reliable for specific format negotiations (like `FLOAT_LE`) and may lead to "cannot set sample format" errors.
    *   Typically provides exclusive access to the hardware device.
*   **PulseAudio/PipeWire Input (`-f pulse -i <source_name>`):**
    *   **Recommended method** for desktop Linux.
    *   Leverages the sound server (PipeWire/PulseAudio) for device management, format conversion (if necessary), and sharing.
    *   `ffmpeg` usually takes the stream as provided by the server (often `float32le` if the device supports it).
    *   **Example Command:**
        ```bash
        ffmpeg -f pulse -i alsa_input.usb-ZOOM_Corporation_F3-00.analog-stereo \
               -ac 2 -ar 48000 -c:a pcm_f32le output_session.wav
        ```

## 4. Timestamping Strategies for A/V Sync

The main challenge is **clock drift** between the audio recording computer and the video camera over long durations.

*   **A. Script's Intended Start Timestamp (`Ts`):**
    *   Captured in the shell script using `date --iso-8601=ns | sed 's/,/./g'` immediately before launching `ffmpeg`.
    *   Represents the NTP-synced wall-clock time when the script *intended* the recording session to begin.
    *   Can be embedded into WAV metadata:
        ```bash
        SCRIPT_TIMESTAMP=$(date --iso-8601=ns | sed 's/,/./g')
        ffmpeg ... -metadata comment="Session Intended Start (Ts): $SCRIPT_TIMESTAMP" ...
        ```

*   **B. `ffmpeg`'s Reported Stream Start Time (`Tff`):**
    *   `ffmpeg` prints this to its `stderr` output (e.g., `Input #0... start: 1749536991.176616`).
    *   Represents when `ffmpeg`'s input module *actually started processing audio samples*.
    *   **This is the most accurate timestamp for when audio data flow began for that `ffmpeg` instance.**
    *   Can be captured by redirecting `ffmpeg`'s `stderr` to a log file and then parsing it.
        ```bash
        # In script, after ffmpeg runs and logs to FFMPEG_STDERR_LOG
        FFMPEG_START_EPOCH=$(grep -m 1 -A 1 "Input #0, pulse" "$FFMPEG_STDERR_LOG" | grep -oP 'start: \K[0-9]+\.[0-9]+')
        FFMPEG_START_ISO=$(date -d@"$FFMPEG_START_EPOCH" --iso-8601=ns | sed 's/,/./g')
        # Log FFMPEG_START_ISO to a main session log
        ```

*   **C. Startup Latency (`Tff - Ts`):**
    *   The small delay (typically 1-70ms) between `Ts` and `Tff`.
    *   Caused by script execution, process launch, and `ffmpeg`/sound-server initialization.
    *   Often larger for the very first "cold start" `ffmpeg` run (~30-70ms) and smaller/variable for subsequent "warmed-up" runs (~ +/- 10ms).
    *   Logging both `Ts` (in WAV metadata) and `Tff` (in a separate session log) provides a complete picture. **For critical sync, `Tff` is the reference for audio data start.**

## 5. Long-Term Recording Strategy (e.g., Months)

To manage clock drift and maintain sync:

*   **Regular "Sessions":** Restart the `ffmpeg` recording process at defined intervals (e.g., every 1-4 hours). Each restart creates a new "master" audio recording with a fresh, precise start timestamp.
*   **Precise Session Starts:** Use shell scripting with `date +%s%N`, `bc`, and `sleep` to make the script wake up and initiate new `ffmpeg` sessions as close as possible to desired wall-clock marks (e.g., top of the hour). A `calculate_sleep_until_next_interval()` function is essential.
*   **Recording Lead Time (`RECORDING_LEAD_TIME_SECONDS`):**
    *   The gap between when one `ffmpeg` session ends and the next `MAJOR_INTERVAL_SECONDS` mark.
    *   `ffmpeg` is run with `-t (MAJOR_INTERVAL_SECONDS - RECORDING_LEAD_TIME_SECONDS)`.
    *   Determined empirically; usually 2-5 seconds is very safe (covers `ffmpeg` exit time + script overhead + safety margin).
*   **Internal Segmentation (within a session, optional):**
    *   `ffmpeg ... -f segment -segment_time <chunk_duration> -segment_atclocktime 1 -strftime 1 "segment_name_%Y%m%d-%H%M%S.wav"`
    *   Breaks a long `ffmpeg` session into smaller file chunks (e.g., 10-minute WAVs).
    *   Filenames get second-level wall-clock accuracy.
    *   The primary high-precision timestamp (`Ts` or `Tff`) applies to the *start of the entire `ffmpeg` session*, not individually to each segment file created by this specific muxer from that single `ffmpeg` instance.

## 6. Bash Scripting Notes

*   **Octal Numbers:** Numbers starting with `0` in bash arithmetic `$((...))` are treated as octal. If a variable might contain such a number (e.g., a zero-padded nanosecond string like `087...`), prefix it with `10#` (e.g., `10#$variable`) to force decimal interpretation.
*   **Floating Point Math:** Use `bc -l`.
*   **Locale for Numbers:** Use `LC_ALL=C` before `bc` and `printf "%f"` for consistent `.` decimal separators (e.g., `LC_ALL=C printf "%.3f" "$float_var"`).
*   **Date/Time Conversions:**
    *   ISO with nanoseconds: `date --iso-8601=ns | sed 's/,/./g'`
    *   Filename-friendly: `date +'%Y%m%d-%H%M%S'`
    *   Epoch float to ISO ns: `date -d@FLOAT_EPOCH --iso-8601=ns | sed 's/,/./g'`
    *   ISO to Epoch ns: `date -d"ISO_TIMESTAMP" +%s%N`

## 7. Verification & Post-Production Workflow

1.  **Primary Audio Timestamp:** Use the logged `Tff` (ffmpeg's actual stream start time, captured from its stderr) for each session as the most accurate start time for that block of audio.
2.  **Organizational Timestamp:** The script's `Ts` (embedded in WAV comment as "Script Intended Start") is useful for confirming the script's intended timing and for naming session directories.
3.  **Tools for Metadata:**
    *   `ffprobe -show_format -show_streams file.wav`
    *   `exiftool file.wav` (more comprehensive)
4.  **NLE Sync:**
    *   Align video footage with the corresponding audio session using the audio's `Tff`.
    *   An initial audio-visual slate for the entire project, and potentially periodic slates, are highly recommended for absolute ground-truth and to quantify video camera clock drift.

This approach balances precision, practicality, and robustness for long-duration, synchronized audio-visual recording.
