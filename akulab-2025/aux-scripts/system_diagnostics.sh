#!/bin/bash

echo -e "\n========== A. AUTO-UPDATES ==========\n"

echo "--> /etc/apt/apt.conf.d/20auto-upgrades:"
cat /etc/apt/apt.conf.d/20auto-upgrades 2>/dev/null || echo "❌ File not found"

echo -e "\n--> /etc/apt/apt.conf.d/50unattended-upgrades:"
cat /etc/apt/apt.conf.d/50unattended-upgrades 2>/dev/null || echo "❌ File not found"

echo -e "\n========== B. TIMERS AND CRONTABS ==========\n"

echo "--> systemctl list-timers --all:"
systemctl list-timers --all

echo -e "\n--> /etc/crontab:"
sudo cat /etc/crontab 2>/dev/null || echo "❌ Cannot read /etc/crontab"

echo -e "\n--> /etc/cron.* directories:"
sudo ls -la /etc/cron.* 2>/dev/null

echo -e "\n--> Crontab entries for all users:"
for user in $(cut -f1 -d: /etc/passwd); do
  echo -e "\n# Crontab for $user:"
  sudo crontab -l -u "$user" 2>/dev/null || echo "No crontab for $user"
done

echo -e "\n========== C. RUNNING SERVICES ==========\n"
systemctl list-units --type=service --state=running

echo -e "\n========== D. KERNEL PARAMETERS ==========\n"

echo "--> /boot/firmware/cmdline.txt:"
cat /boot/firmware/cmdline.txt 2>/dev/null || echo "❌ File not found"

echo -e "\n--> /boot/firmware/config.txt:"
cat /boot/firmware/config.txt 2>/dev/null || echo "❌ File not found"

echo -e "\n========== E. SWAP AND FILESYSTEMS ==========\n"

echo "--> Memory and swap usage (free -h):"
free -h

echo -e "\n--> Active swap partitions:"
swapon --show || echo "No active swap"

echo -e "\n--> /etc/fstab:"
cat /etc/fstab 2>/dev/null || echo "❌ Cannot read /etc/fstab"

echo -e "\n--> Mounted filesystems (/dev/*):"
mount | grep "^/dev"

echo -e "\n✅ System diagnostics complete. You can now copy and paste this output to ChatGPT for analysis.\n"

