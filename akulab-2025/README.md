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