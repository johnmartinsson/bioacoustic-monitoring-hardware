# Enable and start the service
sudo cp systemd-services/record_zoom.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now record_zoom.service

# Check logs with:
journalctl -u record_zoom.service -f

# Make sure that the crontab contains
- [ ] backup_recordings.py --rpi=recordingpi
- [ ] rpi_health_snapshot.py

