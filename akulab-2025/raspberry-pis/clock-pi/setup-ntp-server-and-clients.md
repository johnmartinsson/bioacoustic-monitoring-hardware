Okay, let's outline the steps to set up your Raspberry Pi 5 as a Stratum-1 NTP server (Clock Pi) and then configure your Recording Pi to synchronize its time with it.

**Assumptions:**

*   You have two Raspberry Pi 5s: one designated as the "Clock Pi" (NTP server) and the other as the "Recording Pi" (NTP client).
*   You have installed Raspberry Pi OS on both Pis and have network connectivity between them (using the new switch and router setup we discussed).
*   **For Clock Pi Time Source:**
    *   **Scenario 1 (Ideal - GPS):** You have a GPS receiver connected to your Clock Pi (as indicated in your `todo.md`). This will be used as the primary Stratum-1 time source.  You'll need to install GPSD and configure NTP to use it.
    *   **Scenario 2 (Fallback - Internet NTP):** If you don't have a GPS receiver connected *yet*, we can initially configure the Clock Pi to get time from internet NTP servers as a temporary measure. This will be less accurate than GPS but still better than no NTP. You can then switch to GPS later.

**Part 1: Setting up the Clock Pi as an NTP Server (Stratum-1)**

**Choose Time Source for Clock Pi:**

*   **Option A: Using GPS (Stratum-1 Accuracy - Recommended)**

    1.  **Install GPSD and NTP:**
        ```bash
        sudo apt update
        sudo apt install gpsd ntp
        ```

    2.  **Configure GPSD to use your GPS Receiver:**
        *   **Identify your GPS device:**  Typically, USB GPS receivers are often recognized as `/dev/ttyACM0` or `/dev/ttyUSB0`. You can try listing serial ports to help identify it:
            ```bash
            ls /dev/tty*
            ```
        *   **Edit GPSD configuration:** Open the GPSD configuration file:
            ```bash
            sudo nano /etc/default/gpsd
            ```
        *   **Modify the `DEVICES` line:**  Find the line that starts with `DEVICES=`.  Change it to point to your GPS device. For example, if your GPS receiver is at `/dev/ttyACM0`:
            ```
            DEVICES="/dev/ttyACM0"
            ```
            If it's at `/dev/ttyUSB0`:
            ```
            DEVICES="/dev/ttyUSB0"
            ```
            If you are unsure, you can try listing multiple devices:
            ```
            DEVICES="/dev/ttyACM0,/dev/ttyUSB0"
            ```
        *   **Save and Exit:**  Press `Ctrl+X`, then `Y` to save, and `Enter` to exit `nano`.

    3.  **Enable and Start GPSD:**
        ```bash
        sudo systemctl enable gpsd.socket
        sudo systemctl start gpsd.socket
        sudo systemctl enable gpsd
        sudo systemctl start gpsd
        ```

    4.  **Verify GPSD is working and getting a fix:**
        *   Use `cgps -s` (command-line GPS monitor):
            ```bash
            cgps -s
            ```
            You should see output showing GPS data.  Look for:
            *   **`fix: 3D` or `fix: 2D`:** Indicates GPS fix acquired. `3D` is better (latitude, longitude, altitude).
            *   **`time:`:** A valid timestamp.
            *   **`satellites:`:** Number of satellites being tracked (ideally, a good number, like 6 or more).
            *   If you see "no fix" or no time, GPSD may not be communicating with your receiver correctly, or it may need more time outdoors to get a GPS fix.  Ensure your GPS receiver has a clear view of the sky.

    5.  **Configure NTP to use GPSD as a Time Source:**
        *   **Edit NTP configuration file:**
            ```bash
            sudo nano /etc/ntp.conf
            ```
        *   **Comment out or remove existing `server` lines:**  Find lines that start with `server` and put a `#` at the beginning of each line to comment them out (or delete them).  We don't want to use public internet NTP servers as the primary source for the Clock Pi.
        *   **Add lines to use GPSD as a time source:** Add these lines to the `ntp.conf` file:
            ```
            # GPSD time source
            server 127.127.1.0     # Local GPS Receiver
            fudge  127.127.1.0 stratum 1  # Stratum 1 because GPS is highly accurate
            ```
        *   **Local Clock as Fallback (Optional but Recommended):**  It's good practice to have a local clock as a fallback in case GPS signal is lost. Add these lines as well:
            ```
            # Local clock as fallback (if GPS fails)
            server 127.127.1.1     # Local Clock (Undisciplined)
            fudge  127.127.1.1 stratum 10  # Stratum 10 - lower stratum than GPS
            ```
        *   **Restrict Access (Security - Important for NTP Servers):** To prevent your NTP server from being misused on the internet, restrict access to your local network only. Add these lines (adjust `192.168.1.0/24` if your local network is different):
            ```
            restrict default nomodify nopeer noquery limited kod
            restrict 127.0.0.1
            restrict ::1
            restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap
            ```
        *   **Save and Exit:** Press `Ctrl+X`, then `Y` to save, and `Enter` to exit `nano`.

    6.  **Restart NTP Service:**
        ```bash
        sudo systemctl restart ntp
        ```

    7.  **Verify NTP is using GPSD:**
        *   Use `ntpq -p` to check NTP peer status:
            ```bash
            ntpq -p
            ```
            You should see output similar to this (the exact output will vary):
            ```
                 remote           refid      st t when poll reach   delay   offset  jitter
            *GPS_NMEA(0)     .GPS.            0 l    7   64  377    0.000   -0.001   0.001
             LOCAL(0)        .LOCL.         10 l    -   64    0    0.000    0.000   0.000
            ```
            *   **`*GPS_NMEA(0)`:**  The `*` indicates this is the currently selected time source. `GPS_NMEA(0)` shows it's using the GPSD NMEA driver. `refid .GPS.` confirms GPS as the reference. `st 0` means Stratum 0 (effectively Stratum 1 as NTP adds 1 to stratum).
            *   If you see `LOCAL(0)` with a `*`, it means NTP might be using the local clock because GPS is not yet available or configured correctly. Check GPSD status and GPS fix again.

*   **Option B: Using Internet NTP Servers (Temporary Fallback)**

    1.  **Install NTP:**
        ```bash
        sudo apt update
        sudo apt install ntp
        ```

    2.  **Configure NTP to use Public NTP Servers:**
        *   **Edit NTP configuration file:**
            ```bash
            sudo nano /etc/ntp.conf
            ```
        *   **Replace existing `server` lines (if any) with these (or similar public NTP servers):**
            ```
            server 0.pool.ntp.org iburst
            server 1.pool.ntp.org iburst
            server 2.pool.ntp.org iburst
            server 3.pool.ntp.org iburst
            ```
            These lines use the `pool.ntp.org` project which provides a pool of public NTP servers. `iburst` is an option to speed up initial synchronization.
        *   **Restrict Access (Security - Important for NTP Servers):** Add the same `restrict` lines as in Option A to limit access to your local network:
            ```
            restrict default nomodify nopeer noquery limited kod
            restrict 127.0.0.1
            restrict ::1
            restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap
            ```
        *   **Save and Exit:** Press `Ctrl+X`, then `Y` to save, and `Enter` to exit `nano`.

    3.  **Restart NTP Service:**
        ```bash
        sudo systemctl restart ntp
        ```

    4.  **Verify NTP is synchronizing:**
        *   Use `ntpq -p` to check NTP peer status:
            ```bash
            ntpq -p
            ```
            You should see output similar to this (the exact servers and stratum will vary):
            ```
                 remote           refid      st t when poll reach   delay   offset  jitter
            *time.cloudflare .PTB.            2 u   58   64  377   9.788   -0.239   0.025
             +time.google.com .GOOG.          1 u   54   64  377   9.968   -0.432   0.030
             -time-a-g.nist.g .NIST.          2 u   57   64  377   9.923   -0.204   0.027
             ~t2.time.bf1.yaa .BF1.           2 u   56   64  377  10.591   -0.312   0.029
            ```
            *   **`*time.cloudflare ...`:** The `*` indicates the currently selected server.  `st 2` means Stratum 2 (as public internet servers are typically Stratum 2 or higher).
            *   Look for `reach 377` (in octal, which is decimal 255). This means NTP has successfully reached and synchronized with the server.

**Part 2: Configuring the Recording Pi to be an NTP Client**

1.  **Install NTP Client Software:** (If not already installed - Raspberry Pi OS often has `ntpdate` or `ntp` pre-installed, but ensure `ntp` is there):
    ```bash
    sudo apt update
    sudo apt install ntp
    ```

2.  **Configure Recording Pi to Point to Clock Pi:**
    *   **Edit NTP configuration file:**
        ```bash
        sudo nano /etc/ntp.conf
        ```
    *   **Comment out or remove existing `server` lines:**  Similar to the Clock Pi setup, comment out or remove any existing `server` lines.
    *   **Add a `server` line pointing to your Clock Pi's IP address:**  Replace `192.168.1.100` with the **actual IP address of your Clock Pi** on your local network.  If you set a static DHCP lease for it, use that IP.  Let's assume the Clock Pi's IP is `192.168.1.143`.
        ```
        server 192.168.1.143 iburst
        ```
        `iburst` option speeds up initial sync.
    *   **Keep `restrict` lines for security:**  It's still good practice to have basic restrict lines, even on the client:
        ```
        restrict default nomodify nopeer noquery limited kod
        restrict 127.0.0.1
        restrict ::1
        restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap  # Allow sync from local network
        ```
    *   **Save and Exit:** Press `Ctrl+X`, then `Y` to save, and `Enter` to exit `nano`.

3.  **Restart NTP Service on Recording Pi:**
    ```bash
    sudo systemctl restart ntp
    ```

4.  **Verify Time Synchronization on Recording Pi:**
    *   Use `ntpq -p` on the **Recording Pi** to check peer status:
        ```bash
        ntpq -p
        ```
        You should see output like this (the exact name/IP of your Clock Pi will be shown):
        ```
             remote           refid      st t when poll reach   delay   offset  jitter
        *clock-pi.akulab  192.168.1.143  2 u    8   64  377    0.854   -0.015   0.005
        ```
        *   **`*clock-pi.akulab ...` (or IP address):** The `*` indicates this is the currently selected server.  It should show the hostname or IP address of your Clock Pi.
        *   **`refid 192.168.1.143` (or similar):**  Shows the IP or hostname of the reference server.
        *   **`st 2`:** Stratum 2. If your Clock Pi is Stratum 1 (GPS-based), the Recording Pi will be Stratum 2 (one level below). If Clock Pi is internet-based Stratum 2, Recording Pi might be Stratum 3.
        *   **`reach 377`:**  Indicates successful synchronization.

**Important Notes:**

*   **Firewall:** Ensure your firewall on the Clock Pi (if you have one active, which is less common by default on Raspberry Pi OS for home use) is not blocking NTP traffic (UDP port 123) from your local network.
*   **Network Connectivity:**  Stable network connection between the Clock Pi and Recording Pi is essential for NTP synchronization.
*   **Time Zones:** Set the correct time zone on both Raspberry Pis using `sudo raspi-config` (Localization Options -> Change Timezone).
*   **GPS Fix Time:** If using GPS, the Clock Pi might take some time (especially on the first boot or if GPS receiver has been moved) to acquire a GPS fix and for NTP to synchronize with GPS time. Be patient and check `cgps -s` and `ntpq -p` status periodically.
*   **Stratum Levels:** Stratum levels indicate the distance from a highly accurate reference clock (Stratum 1). Stratum 0 is atomic clocks or GPS. Stratum 1 servers are directly connected to Stratum 0 sources. Stratum 2 servers get time from Stratum 1, and so on. Lower stratum numbers are generally more accurate.

By following these steps, you will have set up your Clock Pi as an NTP server and configured your Recording Pi to reliably synchronize its time with it, ensuring accurate timestamps for your audio recordings. Remember to verify the synchronization using `ntpq -p` on both Pis.

Yes, absolutely! Configuring your NTP server to fall back on internet NTP servers if GPS fails is a very good practice to ensure continued time synchronization even if the GPS signal is lost.  This adds redundancy and improves the overall reliability of your NTP service.

Here's how to configure the Clock Pi's `ntp.conf` file to achieve this fallback:

1.  **Edit the NTP Configuration File on the Clock Pi:**
    ```bash
    sudo nano /etc/ntp.conf
    ```

2.  **Modify the `ntp.conf` file to include both GPS and Internet NTP Servers:**

    You should have the GPS configuration from the previous setup.  Now, **add the internet NTP server lines *below* the GPS configuration.**  The complete `ntp.conf` on your Clock Pi should look like this:

    ```
    # GPSD time source (Primary - Stratum 1)
    server 127.127.1.0     # Local GPS Receiver
    fudge  127.127.1.0 stratum 1  # Stratum 1 because GPS is highly accurate

    # Local clock as fallback (if GPS fails - Stratum 10, less preferred than GPS but better than nothing)
    server 127.127.1.1     # Local Clock (Undisciplined)
    fudge  127.127.1.1 stratum 10  # Stratum 10 - lower stratum than GPS, but still fallback

    # Internet NTP Servers as Fallback (If GPS fails - Stratum 3, less preferred than GPS)
    server 0.pool.ntp.org iburst
    server 1.pool.ntp.org iburst
    server 2.pool.ntp.org iburst
    server 3.pool.ntp.org iburst
    fudge time1 stratum 3  # Set stratum for internet servers to 3 (or higher if needed)


    # Restrict Access (Security) - Important for NTP Servers
    restrict default nomodify nopeer noquery limited kod
    restrict 127.0.0.1
    restrict ::1
    restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap
    ```

    **Key Changes and Explanations:**

    *   **GPS Configuration (Remains the same - Stratum 1):**
        ```
        server 127.127.1.0
        fudge  127.127.1.0 stratum 1
        ```
        This section configures GPSD as the primary time source and sets its stratum level to 1, indicating high accuracy.

    *   **Local Clock Fallback (Remains the same - Stratum 10):**
        ```
        server 127.127.1.1
        fudge  127.127.1.1 stratum 10
        ```
        This is the local system clock as a secondary fallback, set to Stratum 10 (less preferred than GPS).

    *   **Internet NTP Servers (Added - Stratum 3):**
        ```
        server 0.pool.ntp.org iburst
        server 1.pool.ntp.org iburst
        server 2.pool.ntp.org iburst
        server 3.pool.ntp.org iburst
        fudge time1 stratum 3  # Set stratum for internet servers to 3
        ```
        *   We've added the `server 0.pool.ntp.org` through `server 3.pool.ntp.org` lines to use public internet NTP servers from the `pool.ntp.org` project.
        *   **`fudge time1 stratum 3`**: This line is crucial. It uses the `fudge` command to **set the stratum level of all the *internet* NTP servers to Stratum 3.**  By setting them to Stratum 3, which is *higher* than the GPS stratum (Stratum 1), we are telling NTP to **prefer the GPS time source whenever it's available.** NTP will only use the internet NTP servers if the GPS source becomes unreachable or unhealthy.
        *   **Stratum Hierarchy:**  The stratum levels now create a preference hierarchy:
            1.  Stratum 1: GPS (Most Preferred)
            2.  Stratum 3: Internet NTP Servers (Fallback if GPS fails)
            3.  Stratum 10: Local Clock (Last Resort Fallback)

    *   **Restrict Access (Security - Remains the same):** The `restrict` lines for security should stay as they are to limit access to your NTP server.

3.  **Save and Exit `ntp.conf`:** Press `Ctrl+X`, then `Y` to save, and `Enter` to exit `nano`.

4.  **Restart the NTP Service on the Clock Pi:**
    ```bash
    sudo systemctl restart ntp
    ```

5.  **Verify NTP Status on Clock Pi:**
    *   Use `ntpq -p` to check the NTP peer status:
        ```bash
        ntpq -p
        ```
        *   When GPS is working, you should still see `*GPS_NMEA(0)` as the active source (Stratum 1).
        *   **To test the fallback:** Temporarily disconnect your GPS receiver from the Clock Pi, or move the Clock Pi indoors where it loses GPS signal.  Wait a few minutes, and then run `ntpq -p` again. You should eventually see NTP switch to using one of the internet NTP servers as the active source (e.g., `*time.cloudflare ...` or similar), and the stratum level will likely be Stratum 2 or 3.  Once you reconnect the GPS and it gets a fix, NTP should automatically switch back to using the GPS source as it's the preferred Stratum 1 source.

**Explanation of Fallback Logic:**

NTP's algorithm automatically selects the best time source based on several factors, including:

*   **Stratum Level:**  Lower stratum levels are preferred (Stratum 1 is best, then Stratum 2, etc.).
*   **Reachability:**  NTP must be able to communicate with the time source.
*   **Jitter and Offset:**  NTP prefers sources with low jitter (time variations) and small offset (time difference).
*   **Stability and Reliability:** NTP tracks the stability and reliability of time sources over time.

By setting the GPS source to Stratum 1 and the internet NTP servers to Stratum 3, you create a clear preference. NTP will always try to synchronize with the Stratum 1 GPS source first. If GPS becomes unavailable, NTP will automatically fall back to using the Stratum 3 internet NTP servers as the next best option.  The local clock (Stratum 10) acts as a last resort if both GPS and internet servers are unreachable.

This configuration provides a robust and reliable NTP service for your Recording Pi, with automatic fallback in case of GPS signal loss.
