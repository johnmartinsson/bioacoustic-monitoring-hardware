# The Akulab Recording Setup


## Recording Pipeline Overview

```
                       [Clock Pi]
                  (Stratum-1 NTP Server)
                      ┌──────────────┐
                      │ GPS-based    │
                      │ time source  │
                      └──────┬───────┘
                             │
                             ▼
        [Recording Pi] (192.168.1.144)
        ┌────────────────────────────────────────────┐
        │ Syncs system clock with Clock Pi (NTP)     │
        │ Records audio to local directory           │
        │ /home/akulab/akulab_2025/audio             │
        │                                            │
        │ Runs local USB backup script               │
        │ → Copies files to attached USB drive       │
        └────────────┬───────────────────────────────┘
                     │ Mounted via SSHFS
                     ▼
        [Analytics Pi]
        ┌─────────────────────────────────────────────────────┐
        │ Mounts:                                             │
        │ - Recording Pi audio directory via SSHFS            │
        │ - NAS audio directory via NFS                       │
        │                                                     │
        │ Runs `backup_recordings.py`:                        │
        │ - Monitors for new, complete files                  │
        │ - Transfers to NAS using rsync                      │
        │ - Verifies file integrity with SHA256 hash          │
        │ - Deletes verified files from Recording Pi          │
        │ - Logs all synced and verified files                │
        └────────────────┬────────────────────────────────────┘
                         │ Mounted via NFS
                         ▼
        [NAS] (192.168.1.196)
        ┌────────────────────────────────────────────┐
        │ Stores verified audio recordings           │
        │ /home/john/akulab_2025/nas/audio           │
        └────────────────────────────────────────────┘
```

---

## Component Roles Summary

### Clock Pi
- Acts as a **Stratum-1 NTP server**, synchronizing time via GPS.
- Provides accurate time to the Recording Pi over the local network.
- ([Could also simply buy a NTP001 from Teltonika.](https://www.dustinhome.se/product/5020038273/ntp001-ntp-server))

### Recording Pi
- Records audio files to local storage.
- Syncs system time from Clock Pi to ensure timestamp accuracy.
- Runs a simple script to back up files to a local USB drive (rsync --verified).
- Shares its audio directory with the Analytics Pi via SSHFS.

### Analytics Pi
- Mounts directories from both the Recording Pi (SSHFS) and NAS (NFS).
- Runs the backup and verification script:
  - Detects new and complete files.
  - Transfers files to NAS using `rsync --verified`.
  - Maintains logs of transferred and verified files.
- Pools all logs and push weekly/daily status update

### NAS
- Serves as long-term storage for verified audio recordings.
- Receives files via NFS mount from the Analytics Pi.

### USB Drive (on Recording Pi)
- Acts as a local backup destination.
- Files are copied via a basic script with no hash verification.

---

# Changes During Recording Season

### Audio-capture command updated at **2025-05-20 T16 18 45 Z**

| Aspect                          | **Previous command**                                                                                    | **New command (2025-05-20)**                        | Practical effect                                                                                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Filename pattern**            | `auklab_zoom_f8_pro_%Y%m%d_%H%M%S_%04d.wav`                                                             | `auklab_%Y%m%dT%H%M%S.wav`                          | • ISO-8601 style (`YYYYMMDDTHHMMSS`) matches camera files.  <br>• Per-segment index (`_%04d`) removed because files now start exactly on the real-time boundary.             |
| **ALSA buffer / period**        | `-B 5000000 -F 1000000`  (5 s / 1 s)                                                                    | `-B 250000 -F 20000`  (250 ms / 20 ms)              | • Capture-to-timestamp latency shrinks from ≤ 1 s to **≤ 20 ms**. <br>• Still \~12 periods of safety against disk stalls.                                                    |
| **Wall-clock stamping**         | none (FFmpeg used monotonic sample count)                                                               | `-use_wallclock_as_timestamps 1` before `-i pipe:0` | • Every audio packet now carries **absolute UTC PTS**, phase-locked to the Stratum-1 NTP server.  <br>• Makes cross-correlation with camera audio a one-off constant offset. |
| **FFmpeg options consolidated** | separate long lines                                                                                     | combined / reordered                                | No functional change—just cleaner.                                                                                                                                           |
| **`creation_time` tag**         | static value at script launch (same in every chunk)                                                     | unchanged (still static) †                          | If per-file timestamps are needed, add a nightly post-stamp or drop the tag.  PTS + filename already encode exact start time.                                                |
| **Other flags kept**            | `pcm_f32le`, `-rf64 always`, `-write_bext 1`, `segment_time`, `segment_atclocktime`, `reset_timestamps` | unchanged                                           | Files stay RF64-safe, 10-min chunks start on clock boundary, contain BWF metadata.                                                                                           |

† **Static `creation_time`**: the tag is evaluated once when the script starts, so it is identical in all segments recorded in that session.  This is expected; absolute timing now lives in the packet PTS and the filename.

---

#### Net result from 16:18:45 Z onward

* **Latency** from microphone diaphragm to recorded timestamp dropped by \~980 ms.
* **Timestamps** are in the **same UTC domain** as the cameras (which also now use wall-clock PTS), simplifying A/V alignment.
* **Filenames** are uniform across audio and video, easing automated pairing and archive lookup.

These changes apply to every WAV chunk whose first filename timestamp is **≥ 20250520T161800**, marking the switchover point.

