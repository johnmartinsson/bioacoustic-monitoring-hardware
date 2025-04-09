# Credit Statement
Thank you [Tiago Freire](https://github.com/tiagofreire-pt) for the [really nice tutorial on how to setup a Stratum-1 NTP server using an Uputronics GPS HAT and a Raspberry Pi 5](https://github.com/tiagofreire-pt/rpi_uputronics_stratum1_chrony/tree/main).

Also, thank you [Jeff Geerling](https://www.jeffgeerling.com/), for a really helpful [overview of how time is kept on our devices](https://www.jeffgeerling.com/blog/2025/diy-ptp-grandmaster-clock-raspberry-pi). That was really helpful.

# Caution
Most of the below content has been created together with ChatGPT-o4, so be cautions. I have tried it, and it has worked, but I can give no guaranteees.

Below is my [concise breakdown of the **“Setup the server”** guide](https://github.com/tiagofreire-pt/rpi_uputronics_stratum1_chrony) from the repository—focusing on what each command or file edit actually *does*, *why* you might want to do it, and which steps are truly **required** for getting a functioning Stratum‑1 GPS/PPS Chrony NTP server vs. which are purely **optimizations**.


---
## 1. System Update and Package Installation

```
sudo apt update && sudo apt upgrade -y
sudo apt install gpsd gpsd-tools gpsd-clients pps-tools chrony minicom gnuplot setserial i2c-tools python3-smbus -y
```

- **What it does**  
  1. `apt update && apt upgrade -y`  
     - Checks for and installs the latest packages/patches on your Raspberry Pi OS.  
  2. `apt install gpsd gpsd-tools gpsd-clients pps-tools chrony minicom gnuplot setserial i2c-tools python3-smbus -y`  
     - **gpsd** + **gpsd-tools** + **gpsd-clients**: Required to interface with GPS hardware, parse GPS data, and provide it to the OS.  
     - **pps-tools**: Utilities for “Pulse-Per-Second” support (a precise timing signal from the GPS).  
     - **chrony**: The NTP server/client software you will be using (instead of the older `ntpd`).  
     - **minicom**: A handy serial terminal program if you want to debug the GPS over serial.  
     - **gnuplot**: Graphing tool (used by that optional log_temp_freq script).  
     - **setserial**: Utility for configuring serial port features such as low_latency.  
     - **i2c-tools** + **python3-smbus**: Let you interact with I2C devices (RTC on the GPS HAT, for instance).

- **Required or optional?**  
  - **Required**: Installing `gpsd`, `chrony`, `pps-tools` is essential.  
  - **Optional**: `minicom`, `gnuplot`, `setserial`, `i2c-tools`, `python3-smbus` are mostly convenience or advanced usage. You *can* omit them if you want a basic system.

---

## 2. Disable the Serial Console on ttyAMA0

```
sudo systemctl disable --now serial-getty@ttyAMA0.service
sudo systemctl disable --now hciuart
```

- **What it does**  
  - By default, Raspberry Pi OS often uses the onboard UART (ttyAMA0) for serial console or Bluetooth. For a GPS HAT, you want `ttyAMA0` free so gpsd can directly read the GPS data (NMEA sentences).  
  - Disabling `serial-getty@ttyAMA0.service` prevents the system from treating `ttyAMA0` as a login console.  
  - Stopping `hciuart` helps if Bluetooth was mapped to the same UART.  

- **Required or optional?**  
  - **Required** for a Pi that’s using GPIO pins 14 & 15 for the GPS (i.e. the “real” UART). If you do not disable the console on that port, it conflicts with GPS usage.

---

## 3. Remove Any Kernel Console Parameters in `/boot/firmware/cmdline.txt`

> *Edit* `/boot/firmware/cmdline.txt`
> Remove `console=serial0,115200` and (if present) `kgdboc=ttyAMA0,115200`

- **What it does**  
  - Similar reasoning to #2: if the kernel is configured to output logs via serial, you want to turn that off so your GPS data won’t clash with system logging on the same pins.

- **Required or optional?**  
  - **Required** so the GPS can use the UART fully.

---

## 4. Edit `/boot/firmware/config.txt` to Enable the GPS HAT’s Features

```
[pi5]
# To enable hardware serial UART interface on GPIO 14/15
dtparam=uart0_console=on
dtoverlay=uart0-pi5

# Disables internal RTC, enables fan, etc. ...
dtparam=rtc=off
...
[all]
dtoverlay=miniuart-bt
dtoverlay=disable-bt
dtoverlay=disable-wifi
...
dtoverlay=i2c-rtc,rv3028,wakeup-source,backup-switchover-mode=3
dtoverlay=pps-gpio,gpiopin=18
init_uart_baud=115200
nohz=off
force_turbo=1
```

- **What it does**  
  1. **`dtparam=uart0_console=on` / `dtoverlay=uart0-pi5`**  
     - Tells Pi 5’s firmware: “Enable the primary UART on GPIO pins 14 (TX) and 15 (RX).” (Model 5 is new, so these overlays differ from older Pis).  
  2. **Disable internal RTC** (`dtparam=rtc=off`)  
     - Pi 5 has an onboard PMIC-based RTC that may conflict with your external GPS HAT’s RTC. Disabling it avoids confusion.  
  3. **Disable Bluetooth / Wi-Fi**  
     - Minimizes electromagnetic interference that can degrade GPS performance and simplifies using the main UART for GPS.  
     - **Optional** if you want to keep Wi-Fi, just remove or comment out `dtoverlay=disable-wifi` or `dtoverlay=disable-bt`.  
  4. **`dtoverlay=pps-gpio,gpiopin=18`**  
     - Tells the OS that on GPIO pin 18 there is a PPS (pulse-per-second) signal. This is *critical* to get sub‑microsecond timing from the GPS.  
  5. **`init_uart_baud=115200`**  
     - Sets a default UART speed.  
  6. **`nohz=off`**  
     - Disables certain kernel tickless features that can add timing jitter.  
  7. **`force_turbo=1`**  
     - Forces the CPU to run at max frequency all the time—reducing clock drift and improving PPS timing consistency.  

- **Required or optional?**  
  - **Most of these are required** if you want: 
    - The GPS UART to appear as `/dev/ttyAMA0`  
    - PPS on GPIO 18  
    - i2c RTC to function (if you want the hardware clock)  
  - **Disabling Wi-Fi/Bluetooth** is *optional*, but recommended for a high-accuracy time server.

---

## 5. Remove NTP Options from DHCP / Disable systemd-timesyncd

```
sudo rm /etc/dhcp/dhclient-exit-hooks.d/timesyncd
sudo nano /etc/dhcp/dhclient.conf
# remove 'dhcp6.sntp-servers' references
sudo systemctl disable --now systemd-timesyncd
```

- **What it does**  
  - Prevents DHCP from injecting other NTP servers into your system and stops `systemd-timesyncd` from conflicting with Chrony.  

- **Required or optional?**  
  - **Required** if you want Chrony as the only time sync. Two competing NTP/time daemons cause confusion.

---

## 6. Lower Serial Latency with Udev Rule

```
sudo nano /etc/udev/rules.d/gps.rules

KERNEL=="ttyAMA0", RUN+="/bin/setserial /dev/ttyAMA0 low_latency"
```

- **What it does**  
  - By default, the UART driver can buffer data in a way that adds microseconds or milliseconds of latency. The `setserial low_latency` option helps the GPS data be handled as fast as possible.  

- **Required or optional?**  
  - **Optional**—but strongly recommended for the best PPS stability.

---

## 7. Force CPU Governor to ‘performance’

```
sudo sed -i  's/CPU_DEFAULT_GOVERNOR="\${CPU_DEFAULT_GOVERNOR:-ondemand}"/CPU_DEFAULT_GOVERNOR="\${CPU_DEFAULT_GOVERNOR:-performance}"/ ...' /etc/init.d/raspi-config
```

- **What it does**  
  - On Raspberry Pi, the default CPU frequency scaling is “ondemand,” meaning it goes up/down with load. For timekeeping, you want a stable CPU frequency. Setting “performance” keeps it pinned at max.  

- **Required or optional?**  
  - **Optional** but recommended if you care about microsecond-level stability. If you do not mind some minor drift, you can skip it.

### 2. If `/etc/init.d/raspi-config` Doesn’t Exist On Your System

Many modern Raspberry Pi OS installations (especially Debian Bookworm–based) no longer have that init script. Instead, there is:
- `/usr/bin/raspi-config` (the interactive menu tool), or  
- The system might handle CPU frequency scaling differently.  

To **set the CPU governor to `performance`** persistently these days, a simpler approach is to **mask or disable** the built-in `ondemand` service, and then manually set `performance` at boot using a small systemd service. For example:

#### Approach A: Disable the ondemand service

1. Check for the “ondemand” service:
   ```bash
   systemctl status ondemand
   ```
   If it exists and is active, you can disable and stop it:
   ```bash
   sudo systemctl disable ondemand
   sudo systemctl stop ondemand
   ```
   This prevents the Pi from automatically setting the CPU governor back to “ondemand.”

2. Manually set the governor to `performance` now:
   ```bash
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```
   You can confirm it worked with:
   ```bash
   cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
   # should say "performance"
   ```

This **will not** survive a reboot by default unless the `ondemand` service is fully disabled or a different script reapplies “ondemand.” Hence step (1) above.

#### Approach B: Create a mini systemd service to set the governor

You can also make a small systemd unit, for instance `/etc/systemd/system/perf-governor.service`:

```ini
[Unit]
Description=Set CPU governor to performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c "echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Then enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable perf-governor.service
sudo systemctl start perf-governor.service
```
That ensures “performance” mode is applied at boot automatically.

---

I used Approach B.

## 8. Disable Fake Hardware Clock

```
sudo systemctl disable --now fake-hwclock
sudo update-rc.d -f fake-hwclock remove
sudo apt-get remove fake-hwclock -y
sudo sed -i '/if \[ -e \/run\/systemd\/system \] ; then/,/\/sbin\/hwclock/ s/^/#/' /lib/udev/hwclock-set
```

- **What it does**  
  - The `fake-hwclock` package tries to store the Pi’s system time on shutdown and restore it on boot. If you have a real RTC on the GPS HAT, you do *not* want a “fake” system time interfering.  

- **Required or optional?**  
  - **Required** if you want the *real* RTC to be used on each boot, rather than the “fake clock” approach.

---

## 9. Reboot

```
sudo reboot
```

- **What it does**  
  - Applies all the above changes to the kernel, overlays, and config files.

- **Required or optional?**  
  - **Required** for changes that involve the kernel or device tree overlays.

---

## 10. Verify I2C for the GPS HAT’s RTC

```
sudo i2cdetect -y 1
```
- **What it does**  
  - Scans I2C bus #1 and shows if addresses `0x52` or `0x42` are recognized for the RTC and GPS. “UU” means that kernel drivers are actively using them.  

- **Required or optional?**  
  - **Optional**—just a debugging check to confirm the HAT is recognized.

---

## 11. Check the `rv3028` RTC

```
sudo hwclock -r
```
- **What it does**  
  - Reads the hardware clock time. If you get an error, you run:
    ```
    sudo hwclock --systohc -D --noadjfile --utc && sudo hwclock -r
    ```
  - That sets the RTC from the current system time, then reads it back.  

- **Required or optional?**  
  - **Optional** for time stamping on reboot, but recommended if you want the Pi to have a correct time on power-up before GPS fix.

---

## 12. Configure `gpsd`

```
sudo nano /etc/default/gpsd

START_DAEMON="true"
USBAUTO="false"
DEVICES="/dev/ttyAMA0 /dev/pps0"
GPSD_OPTIONS="--nowait --badtime --passive --speed 115200"
```

- **What it does**  
  - Tells `gpsd` to:
    - Start as a daemon  
    - Not auto-probe USB devices  
    - Use `/dev/ttyAMA0` (GPS serial data) and `/dev/pps0` (PPS)  
    - Set the baud rate to 115200, ignore bad timestamps (`--badtime`), and go “passive” (only parse data if a client is listening).  

- **Required or optional?**  
  - **Required** to pass GPS data and the PPS signal to Chrony or other clients.

---

## 13. (Optional) Force the GNSS Module to 115200 bps

```
ubxtool -S 115200
```

- **What it does**  
  - Uses `ubxtool` (part of `gpsd` tools) to reconfigure the GPS to output data at 115,200 baud if it’s not already.  

- **Required or optional?**  
  - **Optional**—only needed if your GPS defaults to a different speed.

---

## 14. Restart `gpsd`

```
sudo systemctl restart gpsd
```

- **What it does**  
  - Activates the new config in `/etc/default/gpsd`.

- **Required or optional?**  
  - **Required** once you have changed the config.

---

## 15. Configure Chrony (`/etc/chrony/chrony.conf`)

I used this config, basically a commented version of [this config](https://github.com/tiagofreire-pt/rpi_uputronics_stratum1_chrony/blob/main/steps/setup_the_server.md#setup-chrony-as-the-service-for-the-ntp-server).

```
#===================================================================
# Welcome to the chrony configuration file.
# See chrony.conf(5) for more information about directives.
#===================================================================

# Load extra config files (ending in .conf) from /etc/chrony/conf.d
confdir /etc/chrony/conf.d

# ----- Pool of Public NTP Servers -----
# Poll interval fixed at 32 seconds, ignoring slow/fast logic.
# Use min/max delay to reject outlier measurements above 30ms or
# 2× the stdev from the minimal delay.
# ‘maxsources 6’ means up to 6 IP addresses can be used.
pool 0.pool.ntp.org iburst minpoll 5 maxpoll 5 polltarget 16 maxdelay 0.030 maxdelaydevratio 2 maxsources 6
pool 1.pool.ntp.org iburst minpoll 5 maxpoll 5 polltarget 16 maxdelay 0.030 maxdelaydevratio 2 maxsources 6

# If you want this Pi to be fully offline/air-gapped, you can disable
# the chronyc command port by uncommenting:
#cmdport 0

# Load NTP sources (server/pool/peer lines) from .sources files in /etc/chrony/sources.d
sourcedir /etc/chrony/sources.d

# Key file for symmetric NTP authentication
keyfile /etc/chrony/chrony.keys

# Save clock drift compensation here
driftfile /var/lib/chrony/chrony.drift

# Save NTS cookies here (for secure time using NTS)
ntsdumpdir /var/lib/chrony

# (Optional) Server certificate and key lines for NTS would go here, commented out
#ntsserverkey /etc/pki/tls/private/foo.example.net.key
#ntsservercert /etc/pki/tls/certs/foo.example.net.crt
#ntsratelimit interval 3 burst 1 leak 2

# Enable more detailed logging
#log tracking measurements statistics 
log rawmeasurements measurements statistics tracking refclocks tempcomp

# Put chrony logs in /var/log/chrony
logdir /var/log/chrony

# Lock chronyd’s memory to avoid being swapped out
lock_all

# Don’t let uncertain measurements drastically skew our system clock
maxupdateskew 100.0

# On startup, if time offset is over 1 second, step immediately,
# else slew. We'll check these fallback servers: time.facebook.com, time.google.com
initstepslew 1 time.facebook.com time.google.com

# Rate-limit NTP responses to misbehaving clients:
# up to 1 response/second, bursting 16, plus partial random leak
ratelimit interval 1 burst 16 leak 2

# Allocate up to 10,000,000 bytes for client logs and interleaved state
clientloglimit 10000000

# Enable kernel synchronization (11-minute mode) of the RTC on Linux
rtcsync

# In the first 3 updates, if offset > 1s, chrony can step the clock
makestep 1 3

# Use system time zone database for leap second info
leapsectz right/UTC

# Allow any IP to use this Pi as an NTP server (comment out for isolated)
allow

# Use DSCP=48 for NTP packets (Expedited Forwarding / QoS)
dscp 48

# Enable hardware timestamping for all interfaces if supported
hwtimestamp *

# ------------------------------------------------------------------
# GPS + PPS input: references for ultra-precise time
# ------------------------------------------------------------------

# Shared Memory #0 from gpsd: label as "GPS"
# poll=2^8=256s, approximate offset/delay to handle overhead
# noselect => don't fully trust it alone for final time
refclock SHM 0 poll 8 refid GPS precision 1e-1 offset 0.090 delay 0.2 noselect

# Shared Memory #1 from gpsd, labeled "PPS", more precise
# prefer => strongly prefer if valid
refclock SHM 1 refid PPS precision 1e-7 prefer

# Direct kernel PPS device (/dev/pps0), locked to "GPS" ref,
# short poll=16s, precision=0.1 microseconds, also prefer
refclock PPS /dev/pps0 lock GPS maxlockage 2 poll 4 refid kPPS precision 1e-7 prefer

# If we want temperature compensation (advanced), uncomment this:
#tempcomp /sys/class/thermal/thermal_zone0/temp 30 /etc/chrony/chrony.tempcomp

```

- **What it does**  
  1. **`pool 0.pool.ntp.org ...`**: Tells Chrony to also use public NTP servers as fallback or sanity check.  
  2. **`log ... tracking refclocks tempcomp`**: Tells Chrony to log various stats for debugging.  
  3. **`lock_all`**: Requests Chrony be locked into RAM to reduce scheduling jitter.  
  4. **`hwtimestamp *`**: Enables hardware timestamping on all NICs that support it (Pi 5’s NIC does).  
  5. **`refclock SHM 0`**: The NMEA data from `gpsd` is made available via “shared memory” (SHM). This line picks that up. We set `noselect` if we only want it for extra data.  
  6. **`refclock SHM 1`** + `refclock PPS /dev/pps0 ... prefer`  
     - Tells Chrony to rely strongly on the PPS signal for precise timing.  

- **Required or optional?**  
  - **Required**: You absolutely must define references so Chrony knows where to get time from the GPS/PPS.  
  - The “pool …” lines are optional if you do not want internet fallback.  
  - “lock_all” is optional but recommended for performance.

---

## 16. Create the Temperature Compensation File (Optional)

```
sudo nano /etc/chrony/chrony.tempcomp

# Example file:
20000 0
21000 0
...
50000 0
...
```

- **What it does**  
  - Chrony can apply an offset to the system clock based on CPU temperature. This is advanced. The file pairs “Temperature” with “Frequency Correction.”  

- **Required or optional?**  
  - **Purely optional**. If you do not plan to do temperature compensation, you can skip.

---

## 17. Restart Chrony

```
sudo systemctl restart chronyd.service
```

- **What it does**  
  - Reloads the configuration.

- **Required** if you changed `/etc/chrony/chrony.conf`.

---

## 18. Confirm Everything with:

```
watch chronyc sources -v
```

- **What it does**  
  - Continuously displays Chrony’s sources, offsets, reachability, etc.  

- **Required or optional?**  
  - **Optional** for debugging, but extremely helpful to confirm that the GPS and PPS are working.

---

# Essential vs. Optional Summary

Below is a high-level separation of absolutely essential steps to get a functioning Stratum‑1 server from GPS/PPS, versus extra steps that improve performance or do housekeeping.

| **Category**              | **Essential**                                                          | **Optional**                                                                                                                                       |
|---------------------------|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Install software**      | gpsd, chrony, pps-tools (and dependencies)                             | minicom, gnuplot, setserial, i2c-tools, python3-smbus                                                                                              |
| **Disable serial console**| Yes (prevents conflicts on `/dev/ttyAMA0`)                             | N/A                                                                                                                                                 |
| **Remove kernel console** | Yes (same reason as above)                                             | N/A                                                                                                                                                 |
| **`/boot/firmware/config.txt`** | The overlays for `uart0-pi5`, `pps-gpio`, enabling I2C, etc.      | Disabling Wi-Fi/Bluetooth is recommended but not mandatory if you can tolerate slightly more interference.                                         |
| **Remove timesyncd**      | Yes (avoids conflict with Chrony)                                      | N/A                                                                                                                                                 |
| **Setserial low_latency** | Strongly recommended for best accuracy                                 | Technically optional, but helps reduce jitter.                                                                                                      |
| **CPU Governor**          | Optional for sub-ms accuracy, recommended for sub-µs or better         | If you do not need extremely good time stability, you can skip forcing the CPU governor to “performance.”                                           |
| **Disable fake-hwclock**  | Recommended if you want to rely on the real RTC on the GPS HAT         | If no RTC is present, or you do not care about correct time on boot, you can skip.                                                                  |
| **I2C/RTC checks**        | Optional but helpful for verifying everything works                    | You can skip if not using the HAT’s RTC.                                                                                                            |
| **`gpsd` config**         | Absolutely required to pass GPS & PPS to Chrony                        | N/A                                                                                                                                                 |
| **`chrony.conf`**         | Absolutely required to specify NMEA + PPS references                   | The advanced features (`lock_all`, `tempcomp`, etc.) are optional.                                                                                  |
| **Temp Compensation**     | Completely optional                                                    | Only needed for ultra-precision.                                                                                                                    |
| **Reboots** / **Service restarts** | Required whenever you make changes that affect the kernel or services | N/A                                                                                                                                                 |

---

## Final Notes

- If you do **only** the essential steps (install the correct packages, disable serial console, point Chrony to your GPS/PPS refclocks, and confirm it), you’ll already have a functioning **Stratum-1** time server.  
- The *optional* steps enhance accuracy, minimize jitter, or avoid edge cases. Most are worthwhile if you want to push the Pi 5 + GPS HAT to its best potential.  
- Always verify your final setup with `chronyc sources -v` and `chronyc tracking` to ensure the PPS is actually locked and that your offsets are low.  

I hope this clarifies what each command does, why it’s used, and which ones are truly mandatory vs. purely optimization!
