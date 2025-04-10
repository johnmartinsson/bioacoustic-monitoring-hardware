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
- Runs a simple script to back up files to a local USB drive (no verification).
- Shares its audio directory with the Analytics Pi via SSHFS.

### Analytics Pi
- Mounts directories from both the Recording Pi (SSHFS) and NAS (NFS).
- Runs the backup and verification script:
  - Detects new and complete files.
  - Transfers files to NAS using `rsync`.
  - Verifies file integrity via SHA256 hashes.
  - Deletes verified files from the Recording Pi.
  - Maintains logs of transferred and verified files.

### NAS
- Serves as long-term storage for verified audio recordings.
- Receives files via NFS mount from the Analytics Pi.

### USB Drive (on Recording Pi)
- Acts as a local backup destination.
- Files are copied via a basic script with no hash verification.

---

## Tested 2025-03-28

The setup has been tested by mounting the recording pi audio directory and using a laptop to act as the NAS by simply creating a directory. Recording is done on the recording pi, and then everything is transferred and verified by the analytics pi. Example output below:

```
sent 46.091.028 bytes  received 35 bytes  4.389.625,05 bytes/sec
total size is 46.079.654  speedup is 1,00
2025-03-28 14:19:18,030 - analytics_pi - INFO - File /home/john/akulab_2025/recording_pi/audio/zoom_audio_20250328_141548_0028.wav successfully transferred to /home/john/akulab_2025/nas/audio/zoom_audio_20250328_141548_0028.wav using rsync.
2025-03-28 14:19:18,031 - analytics_pi - INFO - File zoom_audio_20250328_141548_0028.wav successfully transferred to NAS.
2025-03-28 14:19:18,031 - analytics_pi - INFO - Verifying file zoom_audio_20250328_141548_0028.wav integrity.
2025-03-28 14:19:28,635 - analytics_pi - INFO - File zoom_audio_20250328_141548_0028.wav verified successfully.
2025-03-28 14:19:28,974 - analytics_pi - INFO - File zoom_audio_20250328_141848_0028.wav is not complete yet. Skipping.
2025-03-28 14:19:29,335 - analytics_pi - INFO - File zoom_audio_20250328_141748_0028.wav is not complete yet. Skipping.
sending incremental file list
zoom_audio_20250328_141648_0028.wav

sent 46.091.028 bytes  received 35 bytes  4.007.918,52 bytes/sec
total size is 46.079.654  speedup is 1,00
2025-03-28 14:19:42,044 - analytics_pi - INFO - File /home/john/akulab_2025/recording_pi/audio/zoom_audio_20250328_141648_0028.wav successfully transferred to /home/john/akulab_2025/nas/audio/zoom_audio_20250328_141648_0028.wav using rsync.
2025-03-28 14:19:42,045 - analytics_pi - INFO - File zoom_audio_20250328_141648_0028.wav successfully transferred to NAS.
2025-03-28 14:19:42,045 - analytics_pi - INFO - Verifying file zoom_audio_20250328_141648_0028.wav integrity.
2025-03-28 14:19:53,129 - analytics_pi - INFO - File zoom_audio_20250328_141648_0028.wav verified successfully.
2025-03-28 14:19:53,139 - analytics_pi - INFO - [DRY-RUN] Would remove: /home/john/akulab_2025/recording_pi/audio/zoom_audio_20250328_141548_0028.wav
2025-03-28 14:19:53,139 - analytics_pi - INFO - Removed verified file zoom_audio_20250328_141548_0028.wav from Recording Pi.
2025-03-28 14:19:53,140 - analytics_pi - INFO - [DRY-RUN] Would remove: /home/john/akulab_2025/recording_pi/audio/zoom_audio_20250328_141648_0028.wav
2025-03-28 14:19:53,140 - analytics_pi - INFO - Removed verified file zoom_audio_20250328_141648_0028.wav from Recording Pi.
sending incremental file list
zoom_audio_20250328_141848_0028.wav

sent 46.091.028 bytes  received 35 bytes  4.389.625,05 bytes/sec
total size is 46.079.654  speedup is 1,00
2025-03-28 14:21:05,465 - analytics_pi - INFO - File /home/john/akulab_2025/recording_pi/audio/zoom_audio_20250328_141848_0028.wav successfully transferred to /home/john/akulab_2025/nas/audio/zoom_audio_20250328_141848_0028.wav using rsync.
2025-03-28 14:21:05,466 - analytics_pi - INFO - File zoom_audio_20250328_141848_0028.wav successfully transferred to NAS.
2025-03-28 14:21:05,466 - analytics_pi - INFO - Verifying file zoom_audio_20250328_141848_0028.wav integrity.
2025-03-28 14:21:15,364 - analytics_pi - INFO - File zoom_audio_20250328_141848_0028.wav verified successfully.
2025-03-28 14:21:15,417 - analytics_pi - INFO - File zoom_audio_20250328_142048_0028.wav is not complete yet. Skipping.
sending incremental file list
zoom_audio_20250328_141748_0028.wav
```


### Starting the Recording Pipeline
On each pi

```
git clone ...
cd bioacoustic-monitoring-hardware/akulab/
```

## Recording pi

```
bash recording_pi.sh
```

## Clock pi

```
bash clock_pi.sh
```

## Analytics pi

```
bash analytics_pi.sh
```

## Log files
