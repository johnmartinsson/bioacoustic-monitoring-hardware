Here's a compact and helpful **README** you can drop into your project or use as a quick reference, including a **single bash command** to tail all relevant logs for:

- 🛠 **Systemd services**:
  - `record_zoom.service`
  - `mount_nas.service`
  - `mount_recording_pi.service`
- ⏰ **Cron jobs**:
  - `rpi_health_snapshot.py`
  - `backup_recordings.py`

---

## ✅ `README.md` for Logs and Status

```markdown
# 📊 Monitoring Akulab 2025 System Health

This project uses both **systemd services** and **cron jobs** to automate recording and data management.

---

## 🔍 View Systemd Service Logs

Run this to view logs for recording and mount services:

```bash
journalctl -u record_zoom.service -u mount_nas.service -u mount_recording_pi.service -n 50 --no-pager
```

Use `-f` to follow live:

```bash
journalctl -u record_zoom.service -u mount_nas.service -u mount_recording_pi.service -f
```

---

## ⏰ View Cron Job Logs

If cron output is redirected to a log (recommended), check:

```bash
tail -n 50 /home/analyticspi/cron.log
```

If not using redirected logs, check system logs:

```bash
journalctl | grep CRON | grep -E "rpi_health_snapshot|backup_recordings"
```

To search for any recent failures:

```bash
grep -i "error\|fail" /home/analyticspi/cron.log
```

---

## ✅ Quick Health Check Command (tail all logs together)

```bash
# Tail all relevant logs at once (edit paths/user as needed)
tail -n 20 /home/analyticspi/cron.log && echo "----- SYSTEMD SERVICES -----" && journalctl -u record_zoom.service -u mount_nas.service -u mount_recording_pi.service -n 20 --no-pager
```

Add this as an alias in your shell for convenience:

```bash
alias healthcheck='tail -n 20 ~/cron.log && echo "----- SYSTEMD SERVICES -----" && journalctl -u record_zoom.service -u mount_nas.service -u mount_recording_pi.service -n 20 --no-pager'
```

---

## 🔄 Status Overview

```bash
# Check if all services are running
systemctl status record_zoom.service mount_nas.service mount_recording_pi.service
```
```

---

