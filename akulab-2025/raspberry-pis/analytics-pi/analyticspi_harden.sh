#!/usr/bin/env bash
# === ANALYTICS PI HARDENING SCRIPT ===
set -e
LOG=/root/hardening.log
exec > >(tee -a "$LOG") 2>&1

echo "=== Analytics‑Pi hardening started $(date) ==="

###############################################################################
# 1. Disable update / maintenance timers (same as others)
###############################################################################
systemctl disable --now apt-daily.timer apt-daily-upgrade.timer man-db.timer \
                          e2scrub_all.timer fstrim.timer
systemctl mask  apt-daily.service apt-daily-upgrade.service man-db.service \
                e2scrub_all.service

###############################################################################
# 2. OPTIONAL fake‑hwclock removal — leave it unless you want *zero* extra writes
###############################################################################
# Uncomment next three lines to remove fake‑hwclock here as well
systemctl disable --now fake-hwclock.service
apt-get -y purge fake-hwclock
sed -i '/hwclock-set/ s/^/#/' /lib/udev/hwclock-set

###############################################################################
# 3. Remove swap (lots of rsync writes benefit from no swap)
###############################################################################
dphys-swapfile swapoff || true
dphys-swapfile uninstall || true
systemctl disable dphys-swapfile.service || true
update-rc.d dphys-swapfile remove || true
sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=0/' /etc/dphys-swapfile || true
sed -i 's/rootfstype=ext4/rootfstype=ext4 noswap/' /boot/firmware/cmdline.txt || true

###############################################################################
# 4. Disable unused desktop / peripheral services
###############################################################################
#systemctl disable --now lightdm.service bluetooth.service ModemManager.service \
#                          cups.service cups-browsed.service triggerhappy.service \
#                          serial-getty@ttyAMA10.service || true

# Keep wpa_supplicant if this Pi uses Wi‑Fi; otherwise disable:
# systemctl disable --now wpa_supplicant.service

# 5.  *No* performance‑governor (ondemand fine)

###############################################################################
# 6. Verification one‑shot
###############################################################################
cat > /etc/systemd/system/hardening-verify.service <<'EOF'
[Unit]
Description=Post‑hardening verification (Analytics Pi)

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

echo "=== Analytics‑Pi hardening complete – rebooting... ==="
sleep 2
reboot

