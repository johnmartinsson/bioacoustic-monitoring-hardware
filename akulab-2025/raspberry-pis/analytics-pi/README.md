# Create a systemd user service
mkdir -p ~/.config/systemd/user
cp systemd-services/mount_recording_pi.service ~/.config/systemd/user/mount_recording_pi.service

# Enable the service
systemctl --user daemon-reload
systemctl --user enable --now mount_recording_pi.service

# Enable lingering to run even without interactive login
sudo loginctl enable-linger analyticspi

# View logs
journalctl --user -u mount_recording_pi.service -f

mkdir -p ~/.config/systemd/user
cp systemd-services/*.service ~/.config/systemd/user/
