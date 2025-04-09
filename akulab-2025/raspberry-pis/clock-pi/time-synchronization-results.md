# NTP Synchronization Results

## 1. NTP Client: analyticspi

### chronyc sources -v
```bash
  .-- Source mode  '^' = server, '=' = peer, '#' = local clock.
 / .- Source state '*' = current best, '+' = combined, '-' = not combined,
| /             'x' = may be in error, '~' = too variable, '?' = unusable.
||                                                 .- xxxx [ yyyy ] +/- zzzz
||      Reachability register (octal) -.           |  xxxx = adjusted offset,
||      Log2(Polling interval) --.      |          |  yyyy = measured offset,
||                                \     |          |  zzzz = estimated error.
||                                 |    |           \
MS Name/IP address         Stratum Poll Reach LastRx Last sample               
===============================================================================
^* clockpi                       1   7   377    31    -13us[  -13us] +/-  200us
^- lul2.ntp.netnod.se            1   7   377    33    -69us[  -69us] +/-   14ms
^- h-98-128-230-186.A498.pr>     2   6   377    33    -14us[  -14us] +/-   31ms
^- ntp2.flashdance.cx            2   7   377    29  -2708us[-2708us] +/-   11ms
^- svl2.ntp.netnod.se            1   7   377    31   -669us[ -669us] +/- 9895us
```

**Commentary:**

- The client (analyticspi) has multiple servers listed (public NTP servers plus `clockpi` at the top).  
- An asterisk `^*` next to `clockpi` indicates it is the **current best** synchronization source.  
- The offset is very small (on the order of microseconds), and the estimated error is also small (`+/- 200us`).

### chronyc tracking
```bash
Reference ID    : C0A8018C (clockpi)
Stratum         : 2
Ref time (UTC)  : Wed Apr 09 07:11:07 2025
System time     : 0.000000517 seconds fast of NTP time
Last offset     : +0.000000003 seconds
RMS offset      : 0.000003156 seconds
Frequency       : 4.066 ppm fast
Residual freq   : +0.000 ppm
Skew            : 0.015 ppm
Root delay      : 0.000195510 seconds
Root dispersion : 0.000059909 seconds
Update interval : 64.6 seconds
Leap status     : Normal
```

**Commentary:**

- `Stratum         : 2` means it’s receiving time from a stratum 1 source (the `clockpi` device).
- Offsets are near zero (nanoseconds to microseconds).  
- “Root delay” and “Root dispersion” are both extremely low, indicating minimal network latency to the server.

---

## 2. NTP Server: clockpi

### chronyc sources -v
```bash
  .-- Source mode  '^' = server, '=' = peer, '#' = local clock.
 / .- Source state '*' = current best, '+' = combined, '-' = not combined,
| /             'x' = may be in error, '~' = too variable, '?' = unusable.
||                                                 .- xxxx [ yyyy ] +/- zzzz
||      Reachability register (octal) -.           |  xxxx = adjusted offset,
||      Log2(Polling interval) --.      |          |  yyyy = measured offset,
||                                \     |          |  zzzz = estimated error.
||                                 |    |           \
MS Name/IP address         Stratum Poll Reach LastRx Last sample               
===============================================================================
#? GPS                           0   8   377   167    -40ms[  -40ms] +/-  200ms
#* PPS                           0   4   377    14   +600ns[+3653ns] +/-  653ns
#- kPPS                          0   4   377    14   +584ns[ +584ns] +/-  654ns
^- time100.stupi.se              1   5   377   167   -556us[ -555us] +/- 6955us
^- mmo1.ntp.netnod.se            1   5   377   131   -968us[ -969us] +/- 5987us
^- ntp2.flashdance.cx            2   5   377     4  -2114us[-2114us] +/- 9434us
^- ntp3.hjelmenterprises.com     4   5   377    39  -3511us[-3508us] +/-   17ms
^- h-98-128-175-45.A785.pri>     2   5   377     2  +6470us[+6470us] +/-   53ms
^- h-98-128-230-186.A498.pr>     2   5   377   229    -56us[  -52us] +/-   29ms
^- time.cloudflare.com           3   5   377   101   -414us[ -414us] +/- 7282us
^- lul1.ntp.netnod.se            1   5   377   262   -358us[ -350us] +/-   13ms
^- svl2.ntp.netnod.se            1   5   377    67   -229us[ -228us] +/- 9283us
^- ntp7.flashdance.cx            2   5   377   195  -3463us[-3462us] +/-   10ms
^- calx.aeza                     2   5   377     6  -1743us[-1740us] +/-   16ms
^- ntp3.flashdance.cx            2   5   377   130  -1283us[-1284us] +/- 8159us
```

**Commentary:**

- The server uses local reference clocks: `GPS`, `PPS`, and `kPPS`.  
- `PPS` has an asterisk `#*`, meaning it’s the current best (the Pi is basically a Stratum 1 source via GPS/PPS).  
- External public NTP servers appear with `^-`, but they are secondary in importance compared to the local hardware time source (PPS).

### chronyc tracking
```bash
Reference ID    : 50505300 (PPS)
Stratum         : 1
Ref time (UTC)  : Wed Apr 09 07:12:20 2025
System time     : 0.000002105 seconds fast of NTP time
Last offset     : +0.000003065 seconds
RMS offset      : 0.000001946 seconds
Frequency       : 1.916 ppm slow
Residual freq   : +0.077 ppm
Skew            : 0.036 ppm
Root delay      : 0.000000001 seconds
Root dispersion : 0.000015331 seconds
Update interval : 16.0 seconds
Leap status     : Normal
```

**Commentary:**

- `Stratum         : 1` indicates this Pi is effectively acting as a primary reference.  
- The `PPS` source is giving microsecond-level accuracy.  
- Extremely low offset, residual frequency, and skew show that the Pi’s clock is very stable.

---

### Overall Remarks

- The **server** (clockpi) is locked to PPS (Pulse Per Second from GPS), giving it Stratum 1 status and very low offsets.  
- The **client** (analyticspi) is syncing to the clockpi, making it a Stratum 2 device with offsets in the microseconds.  
- Both systems indicate **“Leap status : Normal,”** meaning no pending leap second events and full synchronization.  

These logs confirm the Pi-based NTP server is working properly and the LAN client is successfully synchronizing with it at extremely low jitter.
