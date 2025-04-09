Absolutely! Here’s a **comprehensive and clean field checklist** you can use on-site to set up and verify your **LAN-based NTP time sync with Clock Pi**.

It includes:
- Static IP setup
- Editing `chrony.conf`
- Restarting services
- Verifying synchronization
- Plus optional diagnostics and safety steps

You can paste this into your repo or personal notes directly. It's copy-paste friendly and structured to guide you step by step.

---

# ✅ Field Site Setup: NTP Synchronization with Clock Pi

This checklist ensures that **Recording Pi** and **Analytics Pi** are correctly configured to sync their clocks with **Clock Pi (Stratum 1 NTP Server)**.

---

## 🔧 Step 1: Configure Static IPs

Ensure all three Pis have static IP addresses on the same subnet. Example:

| Device         | Hostname        | Example Static IP     |
|----------------|------------------|------------------------|
| Clock Pi       | `clockpi`        | `192.168.1.140`        |
| Analytics Pi   | `analyticspi`    | `192.168.1.141`        |
| Recording Pi   | `recordingpi`    | `192.168.1.142`        |

Edit the network settings on each Pi:
```bash
sudo nano /etc/dhcpcd.conf
```

Add or modify:
```conf
interface eth0
static ip_address=192.168.1.141/24   # Change for each Pi
static routers=192.168.1.1           # Your LAN gateway (optional)
static domain_name_servers=8.8.8.8   # Optional
```

Then reboot to apply:
```bash
sudo reboot
```

---

## ⚙️ Step 2: Configure chrony on Analytics Pi and Recording Pi

1. **Open chrony config file**:
```bash
sudo nano /etc/chrony/chrony.conf
```

2. **Set Clock Pi as NTP server**  
   Replace or add near the top:
```conf
server 192.168.1.140 iburst
```

3. (Optional) **Comment out public NTP pools** if using only LAN:
```conf
# pool 0.debian.pool.ntp.org iburst
# pool 1.debian.pool.ntp.org iburst
```

4. (Optional) **Enable LAN-wide sync** (e.g., if this client may serve others):
```conf
allow 192.168.1.0/24
```

5. **Save and exit** (`Ctrl + O`, `Enter`, then `Ctrl + X`)

---

## 🔄 Step 3: Restart chrony to apply changes
```bash
sudo systemctl restart chrony
```

---

## 🔍 Step 4: Verify Time Sync

Run these on **Analytics Pi** and **Recording Pi** to check sync with Clock Pi:

### Check current time source
```bash
chronyc sources -v
```

- Look for a line like:
  ```
  ^* 192.168.1.140  ...
  ```
  `^*` means Clock Pi is the selected and synced source.

### Check detailed sync stats
```bash
chronyc tracking
```

- Look for:
  - `Stratum : 2` (indicating sync from a Stratum 1 server)
  - `Reference ID : C0A8018C (clockpi)`
  - Offsets in microseconds or nanoseconds

---

## 📋 Optional Diagnostics & Tools

### Watch source updates live
```bash
watch chronyc sources -v
```

### Log time sync stats to file (optional)
```bash
chronyc tracking >> ~/chrony_tracking_log.txt
```

### Query Clock Pi remotely (only if allowed)
```bash
chronyc -h 192.168.1.140 sources
```

> 🔒 Requires `bindcmdaddress` and `cmdallow` configured on Clock Pi.

---

## 🔁 Recommended: Synchronize Hardware Clock (RTC)

If the device has a real-time clock (RTC), synchronize it after time is locked:

```bash
sudo hwclock --systohc
```

This saves the current system time to the RTC, helping preserve time between reboots (especially useful for Recording Pi and Analytics Pi if disconnected from power).

---

## ✅ Summary Checklist

- [ ] Set static IPs on all Pis
- [ ] Add Clock Pi IP to `chrony.conf` on each client
- [ ] Restart chrony service
- [ ] Verify with `chronyc tracking` and `sources -v`
- [ ] (Optional) Sync hardware clock with `hwclock --systohc`
- [ ] (Optional) Comment out public NTP servers for isolated LAN setups

---

Let me know if you want a printable PDF version or if you'd like this in a separate Markdown file!
