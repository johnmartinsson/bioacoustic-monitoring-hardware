# Configuration Checklist

- [ ] Configure recording pi
  - [ ] Setup USB backup script
- [ ] Configure clock pi
  - [ ] Setup NAS server
- [ ] Configure analytics pi
- [ ] Configure playback laptop

# Lab Testing Checklist

- [ ] **Continuous Recording Stress Test (24-72 hours)**
  - [ ] Run continuous audio recording on the Recording Pi.
  - [ ] Verify that `record_zoom_hourly.sh` segments properly.
  - [ ] Confirm logs do not show disk-overflow or CPU overload.
  - [ ] Check that files move to NAS as expected.

- [ ] **Network Failure Simulation**
  - [ ] Disconnect the Analytics Pi from the switch.
  - [ ] Reconnect it and confirm the backup_recordings script resumes.
  - [ ] Verify no partial/corrupted files remain.

- [ ] **Power Outage Simulation**
  - [ ] Cut power to the Recording Pi mid-recording.
  - [ ] Restore power and ensure the Pi boots, resumes recording, and logs any issues.
  - [ ] Confirm no data corruption occurred.

- [ ] **NAS Throughput & Disk Capacity**
  - [ ] Observe rsync speed from Analytics Pi to NAS.
  - [ ] Verify large file copies do not degrade performance for other tasks.
  - [ ] Check that disk usage is logged and no hidden space issues arise.

- [ ] **File Integrity Validation**
  - [ ] Manually modify a .wav file on the Recording Pi to break its hash.
  - [ ] Confirm the analytics script flags a mismatch in the logs.
  - [ ] Check how errors are handled (e.g., is it retried, or skipped?).

- [ ] **Time Sync/Clock Pi Verification**
  - [ ] Let the system run for several days, confirm offset to real-time remains minimal.
  - [ ] Compare Pi system clock vs. reference NTP servers (if available).

- [ ] **Logging & Alert Configuration**
  - [ ] Verify rpi_health_monitor.py logs to the specified file.
  - [ ] Confirm high-temp warnings, low-disk warnings appear in the logs.
  - [ ] Optionally test hooking logs into an email/SMS alert mechanism.

- [ ] **Mount Check & USB Backup**
  - [ ] Ensure the USB mount is recognized, healthy, and has enough free space.
  - [ ] Pull the USB mid-operation. Confirm logs note the unmounted path.
  - [ ] Reinsert and verify logs confirm re-mounted path.

