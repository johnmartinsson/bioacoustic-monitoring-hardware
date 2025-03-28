# The Akulab recording setup

```
vim config.ini
```

Set the relevant IP addresses and so on.

On each pi

```
git clone ...
cd bioacoustic-monitoring-hardware/akulab/
```

## Recording pi

```
bash recording_pi.sh
```

record_zoom_hourly.sh: continuously records files into zoom_recordings/.

backup_recordings.py: syncs new recordings to the NAS.

verify_backup.py: verifies arrivals based on NAS’s hash feedback.

remove_verified_recordings.py: removes older verified files if you exceed max_local_files.

## Clock pi

```
bash clock_pi.sh
```

## Analytics pi

```
bash clock_pi.sh
```

## NAS server

nas_server.py: monitors the nas_directory (where rsync is placing files) and writes their hash to verification_channel.txt.

## Log files

The file pi_synced_files.log is used by backup_recordings.py to avoid resending.

The file nas_synced_files.log is used by nas_server.py to avoid re-reporting a file’s hash.

The file verified_files.log is used by verify_backup.py to track files already verified.
