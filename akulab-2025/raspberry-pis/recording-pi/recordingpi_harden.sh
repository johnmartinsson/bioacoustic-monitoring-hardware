#!/usr/bin/env bash
# === RECORDING PI HARDENING SCRIPT ===
set -e
LOG=/root/hardening.log
exec > >(tee -a "$LOG") 2>&1

echo "=== Recording‑Pi hardening started $(date) ==="

# 1. Disable heavy update / maintenance work
systemctl disable --now apt-daily.timer apt-daily-upgrade.timer man-db.timer \
                          e2scrub_all.timer fstrim.timer
systemctl mask  apt-daily.service apt-daily-upgrade.service man-db.service \
                e2scrub_all.service

# 2. Remove swap – avoids SD wear during long recordings
dphys-swapfile swapoff || true
dphys-swapfile uninstall || true
systemctl disable dphys-swapfile.service || true
update-rc.d dphys-swapfile remove || true
sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=0/' /etc/dphys-swapfile || true
sed -i 's/rootfstype=ext4/rootfstype=ext4 noswap/' /boot/firmware/cmdline.txt || true

# 3. Remove fake‑hwclock (prevents stale timestamps in WAV headers)
systemctl disable --now fake-hwclock.service || true
apt-get -y purge fake-hwclock
sed -i '/hwclock-set/ s/^/#/' /lib/udev/hwclock-set

# 4. Stop unused desktop / peripheral services
systemctl disable --now lightdm.service bluetooth.service ModemManager.service \
                          cups.service cups-browsed.service triggerhappy.service \
                          wpa_supplicant.service serial-getty@ttyAMA10.service || true

# 5.  *No* performance‑governor (ondemand is fine)

# 6. Verification one‑shot
cat > /etc/systemd/system/hardening-verify.service <<'EOF'
[Unit]
Description=Post‑hardening verification (Recording Pi)

[Service]
Type=oneshot
ExecStart=/bin/bash -c '
echo "===== HARDENING VERIFICATION ($(date)) =====" > /root/hardening-verify.log
systemctl list-timers --all | grep -E "apt|man|e2scrub|fstrim" >> /root/hardening-verify.log
echo -e "\nSwap status:" >> /root/hardening-verify.log
swapon --show >> /root/hardening-verify.log
echo -e "\nGovernor:" >> /root/hardening-verify.log
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor >> /root/hardening-verify.log
echo -e "\nFake-hwclock status:" >> /root/hardening-verify.log
systemctl is-enabled fake-hwclock.service >> /root/hardening-verify.log 2>&1
echo "===== END =====" >> /root/hardening-verify.log
'
RemainAfterExit=yes
EOF
systemctl daemon-reload
systemctl enable hardening-verify.service

echo "=== Recording‑Pi hardening complete – rebooting... ==="
sleep 2
reboot

