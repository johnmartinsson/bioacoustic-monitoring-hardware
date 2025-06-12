# Bioacoustic Monitoring Raspberry‑Pi Toolkit

> **Purpose** – This repository holds everything needed to run an *autonomous three‑Pi recording setup* that
>
> 1. **records** multi‑channel 32‑bit float WAVs (Recording Pi),
> 2. **provides Stratum‑1 time** to the LAN (Clock Pi), and
> 3. **backs up, watches health & publishes daily summaries** (Analytics Pi).
>
> All paths and IPs are configurable in a single [`config.ini`](./config.ini).

---

## 1 · Hardware & Roles

| Hostname        | Role                         | What it runs                                                                        | Where it saves data                          |
| --------------- | ---------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------- |
| **clockpi**     | GPS/PPS Stratum‑1 NTP server | `chrony`, health snapshot                                                           | internal µSD                                 |
| **recordingpi** | 8‑ch Zoom F8 Pro capture     | `record_zoom.sh` (systemd), health snapshot, mount‑watchdog                         | USB HDD (`/media/recordingpi/usb_hdd/Audio`) |
| **analyticspi** | backup + log summariser      | `backup_recordings.py`, `pool_logs.sh`, `summarize_daily_logs.py`, NFS/SSHFS mounts | NAS (`/media/nas/Audio`) & local logs        |

> **Tip** – Set static IPs first (see `clock-pi/todo.md`). Everything else depends on the addresses in *config.ini*.

---

## 2 · Directory Map (top level)

```
raspberry-pis/
│ README.md               ← (this file)
│ config.ini              ← all editable settings
│ backup_recordings.py    ← sync script (2 modes)
│ rpi_health_snapshot.py  ← resource metrics → CSV
│ clear_logs.sh           ← wipe & recreate local log dirs
│
├─ analytics-pi/          ← tools that run only on Analytics Pi
├─ clock-pi/              ← hardening + docs for Clock Pi
└─ recording-pi/          ← tools that run only on Recording Pi
```

Each sub‑folder mirrors the *home directory* of its Pi. Copy only the relevant folder to each host, or clone the repo on every Pi and run the per‑Pi scripts.

---

## 3 · Configuration – `config.ini`

```ini
[nas]             # where backups land
nas_ip       = 192.168.1.65           # NAS address
nas_user     = john                   # user for git/html push (optional)
to_audio_dir = /volume1/BSP_data/Audio

[clockpi]         # NTP server
clockpi_ip   = 192.168.1.140
clockpi_user = clockpi

[recordingpi]     # capture host
recordingpi_ip   = 192.168.1.79
recordingpi_user = recordingpi
segment_time     = 600        # seconds per WAV
sample_rate      = 48000      # Hz
# drive mount point derived from to_audio_dir

[analyticspi]     # backup host
analyticspi_ip   = 192.168.1.155
analyticspi_user = analyticspi
from_audio_dir   = /media/recordingpi/Audio  # SSHFS mount
to_audio_dir     = /media/nas/Audio          # NFS mount
verify_sha256    = false                     # enable after testing
```

1. **Edit only the right‑hand sides.**
2. Re‑run any mounting services after a change (`systemctl --user restart mount_*`).

---

## 4 · One‑time Setup per Pi

### Clock Pi

```bash
sudo bash clock-pi/clockpi_harden.sh               # optional but recommended
sudo crontab clock-pi/crontab.txt                  # health CSV every 10 min
```

### Recording Pi

```bash
sudo bash recording-pi/recordingpi_harden.sh       # optional
sudo cp recording-pi/systemd-services/record_zoom.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now record_zoom.service
crontab recording-pi/crontab.txt                   # health + mount watchdog
```

### Analytics Pi

```bash
bash analytics-pi/analyticspi_harden.sh            # as root (optional)
# user‑level services (runs even without login)
mkdir -p ~/.config/systemd/user
cp analytics-pi/systemd-services/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mount_recording_pi.service mount_nas.service

crontab analytics-pi/crontab.txt                   # backups, pooling, summary
```

> If you want Analytics Pi jobs to run without an interactive login, enable lingering:
> `sudo loginctl enable-linger analyticspi`

---

## 5 · Scheduled Tasks at a Glance

| Pi              | Mechanism    | File                         | Schedule                | Purpose                        |
| --------------- | ------------ | ---------------------------- | ----------------------- | ------------------------------ |
| **clockpi**     | Cron         | `clock-pi/crontab.txt`       | every 10 min            | write CSV health snapshot      |
| **recordingpi** | systemd      | `record_zoom.service`        | *always*                | continuous 8‑ch recording      |
|                 | Cron         | `recording-pi/crontab.txt`   | 5/7‑59 \*/10 min        | health snapshot + HDD watchdog |
| **analyticspi** | Cron         | `analytics-pi/crontab.txt`   | staggered 10‑min blocks | see below                      |
|                 | systemd‑user | `mount_recording_pi.service` | at boot & on‑failure    | SSHFS source mount             |
|                 | systemd‑user | `mount_nas.service`          | at boot & on‑failure    | NFS backup mount               |

**Analytics Pi cron breakdown**

```
+05 min  backup_recordings.py        ← pulls finished WAVs to NAS
+07 min  rpi_health_snapshot.py      ← logs CPU/temp/disk/etc.
+15 min  mount_watchdog.sh           ← auto‑remount if above mounts vanish
+25 min  pool_logs.sh + summarize_daily_logs.py  ← rsync logs & build HTML
+27 min  push_summaries.sh           ← commit & push to GitHub Pages
```

---

## 6 · Key Scripts & What They Do

| Script                        | Runs on                            | Highlights                                                                |
| ----------------------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| **backup\_recordings.py**     | Analytics Pi (`--rpi=analyticspi`) | Verifies mounts, rsyncs *complete* WAVs, optional sha256 check            |
| **backup\_recordings.py**     | Recording Pi (`--rpi=recordingpi`) | *Not scheduled here* but available if you want local → USB copies         |
| **rpi\_health\_snapshot.py**  | all Pis                            | CSV per 10 min – CPU%, temp, NTP drift, mount status, Zoom device OK flag |
| **mount\_* scripts*\*         | Analytics Pi                       | `sshfs` record → local, `nfs` NAS → local; retry logic; watchdog loop     |
| **pool\_logs.sh**             | Analytics Pi                       | grabs today’s logs from all Pis via rsync → `~/logs/pooled/`              |
| **summarize\_daily\_logs.py** | Analytics Pi                       | builds `daily_summaries/YYYY-MM-DD_summary.html` with charts & stats      |
| **push\_summaries.sh**        | Analytics Pi                       | copies HTML into Git repo `docs/` → GitHub Pages                          |
| **clear\_logs.sh**            | any                                | wipes all `~/logs/*` folders (use when SD nearly full)                    |

---

## 7 · Where to Look When Things Break

| Symptom               | First log to check                 | Command                                |
| --------------------- | ---------------------------------- | -------------------------------------- |
| Missing WAVs on NAS   | `~/logs/backup_recordings/*.log`   | `less` or `tail -f`                    |
| Recording stopped     | systemd journal on Recording Pi    | `journalctl -u record_zoom.service -f` |
| USB HDD suddenly full | `df -h /media/recordingpi/usb_hdd` | `ncdu` for deep dive                   |
| Mounts disappear      | `~/logs/mount_watchdog/*.log`      | ensure `mount_*` services are active   |
| Overheating           | health CSVs or daily summary table | open latest HTML summary               |
| NTP drift             | `chronyc tracking` / `sources -v`  | compare against Clock Pi               |

> **Tip** – log files older than a week/month are auto‑compressed by logrotate (see `*/logrotate.d/`).

---

## 8 · Routine Maintenance

1. **Disk Space** – USB HDD should have >10 % free to avoid write errors.
2. **Nas Availability** – check NFS share has enough space; `df -h` on Analytics Pi.
3. **Firmware/OS Updates** – run `sudo apt update && sudo apt full-upgrade` during off‑season and reboot.
4. **SMART Health** – on Recording Pi run `sudo smartctl -H /dev/sda` monthly.
5. **Git Pulls** – update scripts with `git pull` on each Pi; reload services if files changed.
6. **Time Sync** – verify Clock Pi’s GPS lock LED (or `chronyc tracking` shows Stratum 1 + PPS).

---

## 9 · Customising the Pipeline

* **Shorter/longer WAV segments** – change `segment_time` (seconds) in `[recordingpi]` section.
* **Different sample‑rate** – edit `sample_rate` likewise *and* adjust Zoom track metadata inside `record_zoom.sh`.
* **Alternate NAS path** – update `[nas] to_audio_dir` and restart `mount_nas.service`.
* **Enable sha256 verification** – set `verify_sha256 = true` in `[analyticspi]`; ensure password‑less SSH from Analytics Pi → Recording Pi.
* **Add new health checks** – extend `rpi_health_snapshot.py` (e.g. GPU temp) then deploy via `git pull` and the cron pick‑up.

---

## 10 · Acknowledgements

* GPS/PPS Stratum‑1 how‑to by **@tiagofreire‑pt**.
* Time‑sync background by **Jeff Geerling**.
* Generated with help from *OpenAI o3*.

---
