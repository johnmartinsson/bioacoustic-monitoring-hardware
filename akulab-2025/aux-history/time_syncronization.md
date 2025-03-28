# Time Sync Audio/Video using Local Stratum-1 RPi 5 NTP Server

I have followed this guide:

- [RPi Stratum-1 NTP Server - Uputronics GPS Hat](https://github.com/tiagofreire-pt/rpi_uputronics_stratum1_chrony)
   - I did not force_turbo and force the CPU govenor always being performance from boot (yet)
   - I did not disable wifi (yet)

Which seems to work nicely:

```
akulab@raspberrypi:~ $ chronyc tracking
Reference ID    : 50505300 (PPS)
Stratum         : 1
Ref time (UTC)  : Mon Mar 24 14:06:43 2025
System time     : 0.000000025 seconds fast of NTP time
Last offset     : -0.000000040 seconds
RMS offset      : 0.000005204 seconds
Frequency       : 0.155 ppm fast
Residual freq   : +0.001 ppm
Skew            : 0.142 ppm
Root delay      : 0.000000001 seconds
Root dispersion : 0.000024024 seconds
Update interval : 16.0 seconds
Leap status     : Normal
```

## Some things that I have learned

- Timecode input to the Zoom F8 Pro is only needed when recording directly onto the internal SD card, so we do not need this when running in audio interface mode.
- When recording the Zoom F8 Pro in audio interface mode the timestamps of samples are set by the system clock and they do not affect the data sample stream. That is, the relative time between sampling pulses is driven by the internal clock of the Zoom, and then this sample stream is only labeled by timestamps from the computer recording the audio as they arrive. These timestamps do not affect the relative time position of the samples, and should not affect any localization performance.
- Timestamps in a recording stream are always created in a monotonically increasing manner, and if corrected for drift, the time is run "fast" or "slow" for a short period of time to adjust to the new time. This is a forward looking operation that corrects time gradually to preserve the monitonic increasing behaviour of the timestamps. We therefore never get overlap or gaps in the timeline of the audio samples.
- An internet based NTP server may be sufficient for synchronization of audio and video.

# Final Audio/Video Sync Proposals
Here is a succinct comparison of the two main approaches—(A) **Local Pi generating LTC + local NTP** vs. (B) **Both Pi and Milestone just syncing to a common public NTP server**—and the impacts on audio and video synchronization. We will look at how each method influences (1) the Zoom’s eight-channel audio alignment and (2) the Zoom-audio–to–Milestone-video sync.

---

## Option A: Local RPi Generating LTC & Serving as the Local NTP Master

- [RPi Stratum-1 NTP Server - Uputronics GPS Hat](https://github.com/tiagofreire-pt/rpi_uputronics_stratum1_chrony)
   - I did not force_turbo and force the CPU govenor always being performance from boot
   - I did not disable wifi
- [RPi Stratum-1 NTP Server - Adafruit GPS Hat](https://www.satsignal.eu/ntp/Raspberry-Pi-NTP.html)

1. **Audio Channel Sync (within Zoom)**  
   - Independent of LTC or NTP. The F8(n) Pro’s internal crystal ensures all 8 channels remain phase‑locked (microseconds). You do not lose per‑channel alignment here.  
   - The LTC feed from the Pi does *not* alter the Zoom’s sample clock. It merely re-labels timecode. So the 8 channels remain in near-perfect sync with each other.

2. **Audio-to-Video Sync**  
   - The Pi is your local time master. Milestone pulls NTP from the Pi. The Zoom is jammed to the Pi’s LTC. Everyone sees the *same* local time-of-day within a few ms, or even better if your LTC generation is well-coded.  
   - Result: Audio timestamps and video timestamps line up to better than ±10 ms (often ±1–2 ms if done carefully).

3. **Reliability & Jitter**  
   - If the Pi is using GPS or a stable reference, your local LTC and NTP is extremely stable. The Zoom can be re-jammed daily or weekly to keep its timecode label from drifting more than a few frames over weeks.  
   - Milestone sees the Pi’s NTP as well. So, if the Pi drifts, the entire system drifts together—keeping audio and video aligned.

### Why This Helps
- Having a local reference that both systems share typically yields tighter synchronization, especially if the Pi or Zoom can run at sub-ms offset from “true” GPS time.  
- Internet NTP can vary by tens of ms, depending on network latency spikes.

---

## Option B: Both Pi and Milestone Rely on an External/Public NTP Server

1. **Audio Channel Sync (within Zoom)**  
   - Exactly the same as above: the 8 channels are locked together inside the Zoom hardware, unaffected by outside time.  
   - The Zoom is not referencing external time for its audio clock, only for timecode labeling. By default, it might run on “Int Free Run,” which is stable to ±0.2 ppm.

2. **Audio-to-Video Sync**  
   - Milestone’s video server queries “pool.ntp.org” or some remote NTP. The Pi can also query the same public server.  
   - The Zoom is jammed only occasionally (if at all) from the Pi, and that Pi is also reliant on an external NTP feed.  
   - Potentially, each system sees slightly different “network path” delays. The Pi might settle at, say, +10 ms offset from actual time, while Milestone might be +25 ms offset. Over the course of days, those offsets might wander by ±10–50 ms.  
   - Your audio files might end up with a timecode that is 10–50 ms different than the Milestone’s clock. That’s usually not enough to cause obvious lipsync issues, but can be noticeable for close study or longer segments.

3. **Reliability & Jitter**  
   - If your external NTP is stable and your network is good, you might keep offsets to ±10 ms or so. In some cases, it can be ±1–2 ms, but it can also spike if the route changes or you lose internet momentarily. Then Milestone’s next poll might be off by 20–30 ms from the Pi’s next poll.  
   - If the internet goes down, each system free-runs on its own local clock. The Zoom drifts ~2 seconds over 120 days; a typical PC might drift even more. So you may see bigger divergences over time.

### Why This Might Be “Good Enough”
- If you only need your final audio to be within, say, 20–50 ms of the video clock, public NTP is often *fine*. 
- If your network is consistent or you have close by NTP servers, the offset might remain in single-digit ms.

---

## Comparing the Two Approaches

| **Factor**             | **A) Local LTC+NTP**                  | **B) Internet NTP**                     |
|------------------------|----------------------------------------|-----------------------------------------|
| Audio channel sync     | Always rock-solid (Zoom’s internal crystal). LTC does *not* affect it. | Same. Zoom’s internal clock ensures each channel is in microsecond sync. |
| Audio ↔ Video offset   | Very tight (±1–10 ms typical). Everyone references the Pi. | Potential 10–50 ms offset or drift, depending on net conditions.          |
| Handling drift over weeks/months | Pi’s LTC can jam the Zoom daily, so minimal drift in timecode labeling. | Zoom might drift ~2 sec per 120 days. You can jam occasionally by manually referencing internet time. |
| Failure modes          | If Pi goes offline, audio still records, but time labels might not re-jam. Video might shift to net NTP or local fallback. | If net is lost, the Pi and Milestone each free-run. Time offsets can grow if local PC clocks drift more than Zoom. |
| Complexity             | Slightly higher (you run your own local LTC and NTP server). | Lower complexity. Each device simply points to the same external NTP.    |
| Overall Sync Accuracy  | **Higher** – single local master means minimal difference in time-of-day across systems. | **Moderate** – typically 10–50 ms if everything is stable, can occasionally be ±1–2 ms or up to ±100 ms if network fluctuations occur. |

---

## Which to Choose?

- **If you need the best possible alignment** between your 8‑channel Zoom recordings and the Milestone video for subsequent correlation (e.g., analyzing exact behavior in video matching sound events within a few ms): **A local Pi LTC+NTP reference** is the cleanest method. Everyone references the same local clock, so you keep them extremely close (ms-level).
- **If small offsets (10–50 ms) are acceptable**, you can rely on a common external NTP server. It often remains “good enough” for many camera + audio use cases. You’d either jam the Zoom’s timecode from the Pi occasionally (the Pi is also net-synced) or let the Zoom free-run. That might occasionally slip tens of ms from the video.

In practical terms, **Option A** is standard in professional film or continuous wildlife audio monitoring, where a local time master ensures consistent offset. **Option B** is simpler if you’re okay with minor network-based drift.


--------------------------------------------------------------------------------
--------------------------------------------------------------------------------



# USB Audio
Yes, you can absolutely connect a Milestone system to your Raspberry Pi GPS NTP server for time synchronization. Milestone VMS (Video Management Systems) are designed to synchronize their system clocks with NTP servers. This is a standard and recommended practice for ensuring accurate timestamps in video recordings and events.

Regarding tagging audio recorded with a USB soundcard with NTP timestamps and your "keep both times" approach, let's break it down:

**Milestone and NTP Synchronization:**

* **Easy Integration:** Milestone systems are typically configured to use NTP servers.  You would simply configure the Milestone server (and potentially recording devices, depending on your Milestone setup) to use the IP address of your Raspberry Pi NTP server.
* **Video Timestamping:** Milestone will use the NTP-synchronized system time to timestamp video recordings and events within the VMS. This will ensure your video streams are accurately timestamped according to your GPS-derived time.

**Audio Timestamping and the "Keep Both Times" Approach:**

Your "keep both times" approach – logging both the USB audio device's internal clock time and the NTP time concurrently – **makes excellent sense** for your application and is likely the most robust and accurate method for your requirements. Here's why and how to proceed:

**Why "Keep Both Times" is a Good Strategy:**

1. **Addressing Audio Clock Drift:** You correctly identify that even a "very accurate" internal clock on the USB soundcard will drift over 120 days. Simply relying on the audio device's clock alone for absolute time reference will become inaccurate.

2. **Avoiding Real-Time NTP Correction Complexity/Imprecision:**  Attempting to directly *correct* the audio device's clock in real-time using NTP is complex and potentially problematic:
    * **USB Audio Device Control:** USB audio devices typically don't expose interfaces to directly adjust their internal clocks based on external time signals like NTP.
    * **Real-time Correction Jitter:** Even if it were possible, real-time corrections based on NTP over a network might introduce small jumps or jitter into the audio timestamps due to network latency variations and NTP correction intervals. This could be detrimental to high-precision time difference of arrival (TDOA) calculations.
    * **Post-Processing Flexibility:** Logging both timestamps gives you the flexibility to perform sophisticated drift correction and mapping in post-processing, where you have more control and can apply smoothing or more advanced algorithms.

3. **Robustness and Independent Time Streams:**  You maintain two independent time streams:
    * **NTP Time:** Provides the accurate, absolute time reference synchronized to GPS.
    * **Audio Device Time:** Captures the high-resolution, relative time within the audio stream, even if it drifts.
    * By logging both, you can bridge the gap and leverage the strengths of each.

**How to Implement "Keep Both Times":**

1. **Audio Recording Software Modification (Ideal):**
   * **If you have control over the audio recording software:**  Modify it to:
      * **Record Audio Samples:** Capture the raw audio data from the USB soundcard.
      * **Timestamp Audio Samples:**  At regular intervals (e.g., for each audio frame or buffer), record the current timestamp from the USB soundcard's internal clock. This timestamp will be relative to the start of the recording or some internal zero point of the audio device.
      * **Simultaneously Log NTP Time:**  At the *same* or very closely synchronized intervals as you record the audio timestamps, also record the current NTP system time (obtained from the operating system's clock, which is synchronized to your NTP server).
      * **Save Log Data:** Store both the audio timestamps and the corresponding NTP timestamps together in a log file, ideally alongside or interleaved with the audio data.

2. **Separate NTP Time Logging Process (Alternative if Software Modification is Limited):**
   * **If you cannot directly modify the audio recording software:** Create a separate process or script that runs concurrently with the audio recording.
   * **Independent NTP Logger:** This script would periodically (at a rate fast enough to capture drift, e.g., every few seconds or even more frequently) query the system time (NTP time) and log it along with a timestamp from the system clock at the moment of querying.
   * **Synchronization Points:**  You'll need to find a way to synchronize the timestamps from this separate NTP log with the timestamps generated by your audio recording software. This might involve:
      * **Starting Both Processes Simultaneously:**  If you can start both the audio recording and the NTP logging process very close in time, you can use the start times as a rough synchronization point.
      * **Manual Synchronization Events:** Introduce manual events (e.g., a clap sound, a specific visual cue) at the beginning and end of recordings that are recorded in both the audio and video streams. These events can be used as anchor points for time alignment in post-processing.

**Post-Processing Mapping and Drift Correction:**

1. **Load Logged Data:** In your post-processing analysis software (e.g., Python with libraries like NumPy, SciPy), load the log data containing both the audio timestamps and the NTP timestamps.

2. **Establish Mapping Relationship:**  You'll have pairs of (audio_timestamp, NTP_timestamp) recorded at intervals. You can use these pairs to model the relationship between the audio clock and NTP time.

3. **Drift Modeling (Linear or More Complex):**
   * **Linear Interpolation (Simple):**  If the drift is relatively linear over short intervals, you can use linear interpolation between the logged NTP timestamps to estimate the NTP time corresponding to any audio timestamp.
   * **Polynomial Fitting (More Complex):** For longer recordings or if you observe non-linear drift, you might fit a polynomial (e.g., quadratic) to the (audio_timestamp, NTP_timestamp) data points. This allows you to model more complex drift patterns.
   * **Kalman Filtering (Advanced):** For very precise drift estimation, especially if there is noise in the NTP or audio timestamps, you could consider using Kalman filtering techniques.

4. **Apply Mapping to Audio Timestamps:**  Once you have a drift model, you can use it to convert every audio timestamp in your recording to its corresponding NTP time.

5. **Sound Localization Analysis:** Now you have audio streams with timestamps that are effectively in NTP time, synchronized with your video streams (which are also in NTP time thanks to Milestone). You can perform your time difference of arrival (TDOA) calculations and sound localization analysis using these synchronized timestamps.

**Accuracy Considerations for Sound Localization:**

* **NTP Accuracy for Mapping:**  While NTP corrections might have some jitter, the overall NTP time provided by your GPS-based server will be accurate enough to establish a reliable mapping for your audio clock drift over 120 days. The *precision* of the audio clock (the resolution of its timestamps) is crucial for TDOA, and your "keep both times" approach preserves this high precision while correcting for long-term drift using NTP as a reference.
* **Audio Clock Stability:** The stability and linearity of the USB soundcard's internal clock will influence how well you can model and correct the drift.  A more stable clock will lead to more accurate drift correction.
* **Logging Frequency:** The frequency at which you log NTP timestamps relative to audio timestamps will impact the accuracy of your drift model. Higher logging frequency generally leads to better accuracy, especially for non-linear drift.
* **Synchronization Point Accuracy (if using separate processes):** If you are using a separate NTP logging process and synchronization points (like manual events), the accuracy of identifying these synchronization points will affect the overall time alignment.

**Practical Steps to Get Started:**

1. **Choose Audio Recording Software:** Select or develop audio recording software that allows you to access the USB soundcard, record raw audio, and ideally log timestamps from the audio device's internal clock.

2. **Implement NTP Time Logging:** Integrate NTP time logging into your audio recording software (or create a separate process).

3. **Test and Calibrate:**
   * **Short Test Recordings:** Do short test recordings (e.g., 1-2 hours) while logging both audio and NTP times.
   * **Analyze Drift:** Analyze the logged data to characterize the drift of your USB audio device's clock relative to NTP time. Determine if the drift is linear or requires a more complex model.
   * **Validate Mapping Accuracy:**  Test your drift correction and mapping process. You could introduce known time offsets in your audio and video streams and verify if your mapping and localization algorithms can accurately recover these offsets.

4. **Long-Duration Recordings:** Once you are confident in your setup and drift correction method, proceed with your 120-day recordings.

**In summary, your "keep both times" approach is the recommended strategy for your high-precision sound localization application. It addresses the audio clock drift issue effectively, avoids the complexities and potential imprecisions of real-time NTP clock correction, and provides the necessary data for accurate post-processing time alignment with your NTP-synchronized video streams.** You will be able to leverage the high accuracy of your GPS NTP server and the high-resolution timestamps of your USB audio device to achieve precise sound localization over your long recording period.

## Read Timestamps from Zoom F8

Yes, the Zoom F8n Pro is *excellent* for your purpose and *definitely* exposes its clock through its Timecode feature.  This is a professional-grade field recorder specifically designed for synchronized audio recording for film, video, and broadcast, where precise timecode is essential.

**The Zoom F8n Pro and Timecode - Your Best Option**

The F8n Pro is *much better* than a generic USB audio interface for your application because it has:

1. **Highly Accurate Timecode (TCXO):**  As you noted in the specs, it has a Temperature Compensated Crystal Oscillator (TCXO) with 0.2 ppm accuracy. This is *incredibly* accurate and stable timekeeping.  It's designed to maintain sync even when powered off and across long recording sessions.

2. **Timecode In/Out (BNC Connectors):**  It has dedicated BNC connectors for Timecode Input and Output. This is a standard professional interface for timecode synchronization.

3. **Timecode Modes:**  It supports various timecode modes (Free Run, Record Run, RTC Run, External Timecode, Jam Sync) giving you flexibility in how you synchronize and manage timecode.

4. **Metadata Support:** It allows you to embed metadata, including timecode, into the audio files (BWF - Broadcast Wave Format), which is crucial for professional workflows.

**Using the F8n Pro's Timecode for "Keep Both Times"**

Instead of trying to get a sample count from a generic USB audio device, you should leverage the F8n Pro's *Timecode* as your primary "audio device time" source. Here's how the "keep both times" approach should be adapted:

1. **F8n Pro as Timecode Source:**
   * **Internal Timecode Generation:**  The F8n Pro can generate its own timecode using its accurate TCXO. You can set it to "Internal Free Run" mode, where it continuously generates timecode.
   * **External Timecode Sync (Optional, but likely not needed for your island setup):** You *could* sync the F8n Pro's timecode to an external timecode source (if you had one), but for your setup with a GPS NTP server, internal timecode generation is probably sufficient.

2. **Logging Process (Revised for Timecode):**

   Your logging process now becomes:

   * **Step 1: Get NTP System Time (Raspberry Pi):** Same as before. Get NTP system time from your Raspberry Pi.

   * **Step 2: Get F8n Pro Timecode:**  This is the key change. You need to *read* the current timecode from the F8n Pro.  There are a few ways you might be able to do this:

      * **Zoom F8 Control App (Most Likely Easiest):**
         * The specs mention a "Zoom F8 Control App for iOS and Android" that allows "wireless remote control, file renaming, and metadata entry."
         * **Check the F8 Control App:**  The app likely *displays* the current Timecode being generated or received by the F8n Pro.  There might even be a way to get the timecode value programmatically through the app's interface or an API (though less likely for a mobile app, but worth investigating).  This would be the *easiest* if the app provides this data.

      * **USB Interface (as Audio Interface or Control):**
         * **USB Audio Interface Mode:** When the F8n Pro is connected to a computer as a USB audio interface, it *might* be possible to access timecode information through the USB audio stream or a control interface.  This is less likely to be a standard feature of USB audio interfaces, but worth checking the F8n Pro's USB documentation.
         * **USB Control Interface (if exists):** The F8n Pro *might* have a USB control protocol that allows you to send commands and receive status information, including timecode. Check the F8n Pro's manuals and SDK (Software Development Kit) if available.

      * **Timecode Output (BNC) and a Timecode Reader (More Complex, Possibly Overkill):**
         * You could configure the F8n Pro to *output* timecode from its BNC Timecode Out connector.
         * You would then need a separate piece of hardware (a "timecode reader" or "timecode analyzer") that can read SMPTE timecode from the BNC output and interface with your Raspberry Pi (e.g., via USB or serial).
         * This is likely **overkill** for your application unless you absolutely need to verify the timecode signal externally.  Using the app or USB interface (if possible) would be much simpler.

   * **Step 3: Log Both Times Together:**  Same as before, log the NTP time and the *F8n Pro Timecode* together in your log file.  The timecode format is typically SMPTE timecode, which looks like `HH:MM:SS:FF` (Hours:Minutes:Seconds:Frames). You'll need to parse this format.  Example log line (CSV):
      ```
      2023-10-27T10:30:00.123456, 1698402600.123456, 01:23:45:29
      ```
      * `2023-10-27T10:30:00.123456` : Log timestamp.
      * `1698402600.123456` : NTP system time.
      * `01:23:45:29` : F8n Pro Timecode (example).

3. **File Index and Synchronization Workflow:**

   * **File Index NTP Times:**  Continue to record the NTP start and end times for each video and audio file in your file index.
   * **Audio Timestamp Source: F8n Pro Timecode:**  Instead of sample counts, your audio timestamps *within* the audio files will now be derived from the F8n Pro's Timecode.
   * **Post-Processing Synchronization:**
      * **Use Logged Timecode and NTP:**  Your log file provides the mapping between the F8n Pro's timecode and NTP time.
      * **Extract Timecode from Audio Files (BWF Metadata):**  The F8n Pro likely embeds timecode into the BWF audio files it records. You can use audio processing libraries or tools that can read BWF metadata to extract the timecode associated with audio samples within the files.
      * **Map Timecode to NTP:**  Use your log data to establish the relationship between the F8n Pro's timecode and NTP time.  Because the F8n Pro's TCXO is so accurate, the drift should be minimal, but your log data will allow you to correct for any residual drift and align everything to absolute NTP time.

**Advantages of Using F8n Pro Timecode:**

* **Extremely Accurate Time Synchronization:** Timecode is designed for precise synchronization in professional audio and video workflows. The F8n Pro's TCXO provides exceptional accuracy.
* **Robust and Reliable:** Timecode is a robust and well-established standard.
* **Professional Workflow Compatibility:** Using timecode makes your audio data compatible with professional audio and video editing software and workflows that rely on timecode for synchronization.
* **Simplified Synchronization Process:**  Using timecode simplifies the synchronization process compared to relying on sample counts from generic USB devices.

**Next Steps - F8n Pro Specific:**

1. **F8n Pro Manual and Documentation:**  **Crucially, download and thoroughly read the Zoom F8n Pro manual.** Look for sections on:
   * Timecode settings and modes.
   * Timecode output options.
   * USB interface and control protocols.
   * Zoom F8 Control App and its features.
   * BWF metadata and timecode embedding.

2. **Experiment with F8n Pro and Control App:**
   * Set up the F8n Pro to generate internal timecode (Free Run mode).
   * Install the Zoom F8 Control App on a phone or tablet.
   * Connect the app to the F8n Pro via Bluetooth.
   * **Explore the app interface to see if it displays the current Timecode.**  Look for any settings or options related to timecode output or data access.

3. **Investigate USB Interface (Manual and SDK if available):**
   * Check the F8n Pro manual for details on its USB interface capabilities beyond just audio interface mode.
   * See if Zoom provides an SDK or API documentation for controlling the F8n Pro over USB.  This might reveal ways to programmatically access timecode.

4. **If Control App or USB Access Works:**
   * Develop your logging script to read Timecode from the F8n Pro (via the app or USB interface) and NTP time from your Raspberry Pi, and log them together.

5. **If Control App/USB Access is Limited (Less Likely, but Possible):**
   * Consider the Timecode Output (BNC) option, but only if simpler methods fail. You'd need to research timecode readers and how to interface them with your Raspberry Pi.

**Millisecond Accuracy is Easily Achievable**

Yes, with the Zoom F8n Pro's timecode and your GPS NTP server, achieving millisecond-level synchronization accuracy for audio and video alignment is *very* easily achievable and will be far more precise than you need for general audio-video alignment. Timecode itself is frame-accurate (typically 24, 25, 30 frames per second and higher), which is much finer than milliseconds.

**In Conclusion**

The Zoom F8n Pro, with its professional Timecode capabilities, is the *ideal* device for your long-duration, synchronized audio recording project. Focus on leveraging its Timecode feature for your "keep both times" approach. Start by exploring the Zoom F8 Control App as the most promising way to access the F8n Pro's Timecode for logging alongside your NTP time.  You will be able to achieve highly accurate and robust audio-video synchronization and sound localization with this setup.

## Grandmaster Clock

Yes, let's explore alternatives to the "keep both times" approach when using the Zoom F8n Pro and consider direct synchronization with a grandmaster clock.  You are right to think about this, as it's a common and often preferred method in professional synchronized audio/video setups.

**Alternative 1: Timecode Jam Sync to a Grandmaster Clock's Timecode Output**

This is a very viable and professional alternative that can potentially offer even tighter synchronization than "keep both times" in some scenarios, although it adds some complexity.

**How it Works:**

1. **Grandmaster Clock with Timecode Output:** You would use a grandmaster clock that is capable of:
   * **Receiving Highly Accurate Time:** From GPS, PTP, and/or NTP.
   * **Outputting SMPTE Timecode:**  Via a BNC connector.  Many professional grandmaster clocks can do this (e.g., some Meinberg or similar time servers might have this option, or dedicated broadcast sync generators).

2. **Zoom F8n Pro Timecode Input (Jam Sync):**
   * You would connect the Timecode Output of the grandmaster clock to the Timecode Input (BNC) on the Zoom F8n Pro.
   * Configure the F8n Pro to operate in "External Timecode" or "Jam Sync" mode. In Jam Sync mode, the F8n Pro will synchronize its internal TCXO clock to the incoming timecode signal.  "Jam Sync" typically means it synchronizes at the moment of connection and then relies on its own accurate TCXO to maintain time, but regularly "jams" or resynchronizes to the external timecode if it's still present.  "External Timecode" mode means it continuously slaves its timecode to the external input.  Check the F8n Pro manual for the exact behavior of these modes.

3. **Video System NTP Synchronization:**
   * Your video recording system (e.g., Milestone server and recording clients) would be synchronized to NTP from the *same* grandmaster clock.  This ensures both the video system and the F8n Pro are ultimately referenced to the same highly accurate time source.

**Pros of Timecode Jam Sync:**

* **Potentially Very High Accuracy:** If the grandmaster clock is highly accurate (GPS-disciplined, PTP-synchronized), and the Jam Sync mechanism of the F8n Pro is effective, you can achieve very tight synchronization between audio and video. Timecode itself is frame-accurate, which is sub-millisecond precision (depending on frame rate).
* **Professional Standard:** Timecode is the industry standard for synchronization in film, broadcast, and professional audio.  It's a robust and reliable method.
* **Direct Synchronization (of Timecode):**  You are directly synchronizing the *timecode* itself on the F8n Pro to an external reference, rather than relying on post-processing drift correction.
* **Simplified Workflow (Potentially):** In some workflows, having timecode directly embedded in the audio files can simplify downstream editing and synchronization with video in professional NLE (Non-Linear Editing) software.

**Cons of Timecode Jam Sync:**

* **Grandmaster Clock Complexity and Cost:**  A grandmaster clock that outputs Timecode and NTP/PTP is more complex and expensive than a simple NTP server like your Raspberry Pi GPS NTP server. You'd need to invest in dedicated hardware.
* **Timecode Cable and Connection:**  You need a physical BNC cable to connect the grandmaster clock's Timecode output to the F8n Pro's Timecode input. This adds a physical connection point and potential point of failure.
* **F8n Pro Jam Sync Accuracy:** The accuracy of the "Jam Sync" process depends on the F8n Pro's implementation.  It's generally very good, but it's worth testing and verifying.
* **Less "Networked" Approach:**  This is a more "hardware-centric" synchronization method compared to purely network-based NTP/PTP.

**Alternative 2:  Attempting NTP Synchronization for Both (Less Ideal for Audio Precision)**

* **Video System - Yes (NTP from Grandmaster):**  Video systems can easily synchronize to NTP from a grandmaster clock.
* **Zoom F8n Pro - No Direct NTP Client (Likely):**  As we discussed before, the Zoom F8n Pro is *not* designed to be an NTP client. It doesn't have network connectivity to directly sync its internal clock to an NTP server.

**Why NTP for the F8n Pro is Problematic for High Precision:**

* **NTP Accuracy Limitations:** While NTP is good for general time synchronization, achieving *sub-millisecond* accuracy consistently over a network for audio timestamping is challenging due to network latency, jitter, and the nature of NTP corrections (which can be stepped adjustments, not continuous smooth adjustments).
* **F8n Pro Design:** The F8n Pro is designed for professional audio synchronization using Timecode, not network-based NTP synchronization of its recording clock.

**Therefore, directly using NTP to synchronize the F8n Pro's *audio timestamps* to the level of precision you need for sound localization is *not* a reliable or recommended approach.**  NTP is excellent for synchronizing the *system clock* of computers (like your video server), but not for directly driving the precise timing of audio recording hardware like the F8n Pro in a millisecond or sub-millisecond accuracy context.

**Comparison and Recommendation:**

| Synchronization Method                      | Accuracy Potential      | Complexity | Cost      | Best Use Case                                                                     |
|-------------------------------------------|--------------------------|------------|-----------|---------------------------------------------------------------------------------|
| **"Keep Both Times" (with F8n Pro Timecode)** | High                     | Moderate   | Low       | Very good balance of accuracy, robustness, cost-effectiveness, and flexibility.  |
| **Timecode Jam Sync (Grandmaster Clock)**    | Very High (Potentially) | Moderate   | Moderate+ | When absolute highest synchronization accuracy is paramount, and budget allows.   |
| **NTP for Both Video & F8n Pro**            | Lower (Audio)            | Low-Med    | Low-Med   | Not recommended for high-precision audio-video sync. Good for general system time. |

**Recommendation:**

For your Baltic Sea island setup, considering your need for millisecond accuracy and the desire for robustness and practicality:

* **Strongly Consider "Keep Both Times" with F8n Pro Timecode:** This remains an excellent and highly recommended approach. It's robust, cost-effective, and leverages the F8n Pro's professional timecode capabilities. You get very good accuracy through post-processing drift correction, and you retain flexibility.

* **Evaluate Timecode Jam Sync if Absolute Highest Accuracy is Essential and Budget Allows:** If you determine that you absolutely need the *absolute highest* level of synchronization accuracy possible, and you are willing to invest in a grandmaster clock with Timecode output and manage the cable connection, then Timecode Jam Sync is a valid option.  However, for many sound localization applications, the "keep both times" approach with the F8n Pro's timecode will likely be more than sufficient and more practical.

**Key Decision Factors:**

* **Accuracy Requirement:** How critical is sub-millisecond synchronization for your sound localization? Milliseconds?  Or is slightly less precise synchronization acceptable?
* **Budget:**  Grandmaster clocks with Timecode output are more expensive.
* **Complexity Tolerance:** Are you comfortable with setting up and managing a more complex synchronization infrastructure (grandmaster clock, timecode cables)?
* **Robustness/Simplicity:**  "Keep both times" can be seen as simpler in terms of hardware setup and potentially more robust because it doesn't rely on a continuous external timecode connection.

**If you choose "Keep Both Times" with F8n Pro Timecode:** You are on a very solid and practical path.  Focus on:

* Accurately logging NTP time and F8n Pro Timecode.
* Building a robust file index.
* Developing a good drift correction model in post-processing.

**If you consider Timecode Jam Sync:**  You'll need to research and procure a suitable grandmaster clock, understand its configuration and Timecode output, and ensure proper Timecode Jam Sync setup on the F8n Pro.

In most practical scenarios for sound localization where millisecond-level accuracy is needed, and considering the balance of accuracy, cost, and complexity, the **"Keep Both Times" approach with the Zoom F8n Pro Timecode is likely the most pragmatic and highly effective solution.** It provides a professional, accurate, and robust synchronization method without unnecessary complexity or expense.

# IP Audio

Based on the provided documentation, Milestone’s video management system (**XProtect VMS**) explicitly relies on **Network Time Protocol (NTP)** for synchronization. The official Milestone documentation emphasizes using an NTP server (either a dedicated NTP server, domain controller, or the VMS server itself acting as an NTP server) for time synchronization.

**Implications for Your Project:**

- **Audio (AoIP / Dante):**
  - Your audio-over-IP setup (using Dante, AES67, or similar) can easily leverage **Precision Time Protocol (PTP)** for synchronization.
  - Dante/AES67 commonly use **PTPv2**, enabling microsecond-level accuracy ideal for audio synchronization.

- **Video (Milestone XProtect):**
  - Milestone systems explicitly recommend or require **NTP**.
  - Cameras and servers synchronize via standard NTP services (Microsoft or 3rd-party NTP servers).

**Can you use PTP directly with Milestone?**

- As of now, Milestone’s documentation does **not indicate support for PTP synchronization**. It explicitly outlines **NTP** as the synchronization standard.
- This means you cannot directly synchronize Milestone’s VMS or cameras using a PTP source without additional bridging solutions.

---

## Recommended Synchronization Strategy for your scenario:

Since your goal is to synchronize audio streams (using AoIP via Dante/PTP) with Milestone-managed IP cameras and video feeds (via NTP), you have two realistic options:

### Option 1 (Hybrid Sync - recommended):

- Set up a reliable **NTP server** as your primary timing reference (this could be a server already running Milestone).
- Sync all your Milestone-managed cameras and servers to this NTP server.
- Install a **PTP Grandmaster clock** (with GPS for absolute accuracy, if possible).
- Configure your **Dante/AES67 audio network** to use the PTP Grandmaster.
- Sync the PTP Grandmaster clock (audio) and NTP server (video) to the same absolute reference (GPS or common stable source). Many professional Grandmaster clocks can output both PTP and NTP simultaneously, ensuring tight synchronization between the two protocols.

**Pros:**
- Best of both worlds: Milestone video infrastructure remains NTP-compliant.
- Audio infrastructure retains PTP’s microsecond-level accuracy.

**Cons:**
- Additional complexity and cost (dedicated Grandmaster clock).

---

### Option 2 (NTP-only, simpler but lower accuracy):

- Use a single NTP server.
- Set Dante network to operate in **AES67 compatibility mode**, which supports PTPv2 derived from NTP. This approach may sacrifice some precision compared to pure PTP setups but will maintain synchronization sufficiently for many applications.

**Pros:**
- Very straightforward and minimal complexity.
- No specialized equipment required.

**Cons:**
- Lower synchronization precision (milliseconds rather than microseconds), may not be ideal for critical audio/video sync scenarios.

---

### Conclusion & Recommended Approach:

Given Milestone's explicit reliance on NTP, you cannot enforce PTP directly on their infrastructure. However, you are **not strictly limited** to NTP alone for audio. The recommended industry-standard solution is a **hybrid approach (Option 1)** using a Grandmaster clock providing both NTP and PTP outputs. This approach ensures:

- Perfect interoperability with Milestone via NTP.
- Precise audio synchronization via PTP for Dante/AES67 audio-over-IP.

This hybrid strategy represents best practice in professional broadcast/IP-audio environments.

Here's a concise and practical summary highlighting the key differences between the synchronization accuracy guarantees of **NTP** (Network Time Protocol) and **PTP** (Precision Time Protocol):

| Aspect                        | NTP (Network Time Protocol)                          | PTP (Precision Time Protocol - IEEE 1588)               |
|-------------------------------|------------------------------------------------------|---------------------------------------------------------|
| **Typical Accuracy**          | Milliseconds (1-10 ms typically)                     | Microseconds or sub-microseconds (<1 µs possible)      |
| **Accuracy Guarantee**        | No strict deterministic guarantees; network-dependent | Deterministic, with clearly defined accuracy levels     |
| **Network Requirements**      | Minimal: Can run over WAN/internet                   | High-quality local networks required for best accuracy  |
| **Infrastructure Complexity** | Simple; can run on standard networks                 | More complex; requires PTP-aware switches for highest precision |
| **Clock Hierarchy**           | Client-server (usually a public NTP server or local server)  | Master-follower (Grandmaster clock, boundary clocks, transparent clocks) |
| **Traffic Type**              | Typically unicast                                    | Multicast or Unicast (PTPv2 supports both; multicast is common) |
| **Use Cases**                 | General IT systems, general video surveillance (e.g., Milestone) | Professional broadcast, audio/video production, Dante/AES67 networks |
| **Failure Mode**              | Graceful drift; relatively large synchronization errors possible | Small and stable synchronization errors; highly stable clocking |

### Practical implications for your scenario:

- **NTP** is sufficient for general video recording (like Milestone XProtect), where millisecond-level accuracy is adequate to synchronize video frames and timestamps. This accuracy is typically sufficient for surveillance video, playback, and security purposes.

- **PTP** is essential for audio networks (Dante/AES67) in professional settings because it delivers sub-microsecond synchronization, necessary for precise phase-alignment and digital audio integrity—especially critical in scenarios involving live audio, multi-microphone arrays, and synchronized video-audio production workflows.

### In short:

- Use **NTP** when "close enough" synchronization is acceptable (milliseconds accuracy).
- Use **PTP** when high-precision synchronization (microsecond accuracy) is required, typically in professional audio or broadcast scenarios.

Given your scenario—integrating audio (AoIP/Dante) with video (Milestone)—the optimal setup would typically use a high-accuracy **PTP** for audio, with a secondary **NTP** service synchronized from the same PTP Grandmaster for Milestone’s video synchronization requirements.

Setting up a hybrid synchronization scenario (PTP for audio and NTP for video) with your RedNet MP8R is achievable but involves careful planning. Below is a clear outline of what you'll need to consider, specifically relating to the **RedNet MP8R** device capabilities and configuration:

---

### 1. **Is Hybrid Sync Tricky to Set Up?**

**Short answer:**  
It is more involved than using NTP or PTP alone, but very manageable with good planning.

**Detailed answer:**  
Hybrid synchronization involves ensuring that both your NTP-based video (Milestone) and your PTP-based audio (RedNet MP8R via Dante) derive their time from a common reference, typically a GPS-based Grandmaster clock. It's straightforward once the concept is understood, but you'll need specialized hardware (PTP Grandmaster with NTP output capability).

---

### 2. **RedNet MP8R and Sync Capabilities**

The RedNet MP8R supports the Dante audio-over-IP protocol, which uses Precision Time Protocol (**PTPv1** or **PTPv2/AES67**) as its synchronization standard:

- **RedNet MP8R Clocking:**
  - Automatically locks to a valid Dante network master (PTP).
  - Can act as the network master if required.
  - Supports pull-up/pull-down sample rates selectable via Dante Controller.

**Important Considerations from the RedNet MP8R Manual:**
- **Clock Source:** The MP8R automatically locks onto the Dante network's clock. If there isn't an existing network master, the MP8R can serve as the master.
- **Supported sample rates:** 44.1 / 48 / 88.2 / 96 / 176.4 / 192 kHz.
- **Redundancy:** Dual Ethernet connections and dual PSU inputs make the MP8R suitable for critical setups. Redundant network connections allow automatic failover.

---

### 3. **Hybrid Sync Setup Steps (Detailed for RedNet MP8R):**

**Step 1: Install a GPS-based Grandmaster Clock**
- Choose a Grandmaster clock device (e.g., Meinberg, Tekron, Evertz, or others).
- Device should provide both:
  - PTP output (IEEE 1588v2), ideally AES67 compliant.
  - NTP output (for Milestone VMS).

**Step 2: Configure Grandmaster**
- Set it up with GPS reference to provide highly accurate UTC-based time.
- Enable both **PTP output** and **NTP output**.

**Step 3: Configure Dante network (RedNet MP8R)**
- Connect the RedNet MP8R (via primary/secondary Dante ports) to a suitable network switch.
- Set Dante network to use the Grandmaster’s PTP clock as the master clock.
- RedNet MP8R will automatically lock to the PTP clock.

**Step 4: Configure Milestone VMS**
- Set Milestone's servers and IP cameras to synchronize with the **NTP output** from the same Grandmaster.
- Confirm NTP synchronization across Milestone servers and cameras.

**Step 5: Confirm Synchronization**
- Once configured, audio and video are synchronized indirectly through a common reference. The video uses NTP, and the audio uses PTP, both tracing back to the same Grandmaster.

---

### 4. **Critical Points to Consider**

- **Switch Compatibility:**  
  PTP accuracy depends on network hardware. Professional-grade switches with IEEE 1588 (PTP-aware switches) are recommended for microsecond-level accuracy.

- **Grandmaster Clock Accuracy:**  
  A GPS-based Grandmaster clock ensures absolute accuracy and a stable common time reference.

- **Network Topology & Traffic Management:**  
  Use VLANs to separate audio (PTP) from general network traffic to ensure timing accuracy and minimize jitter.

- **RedNet Control Software:**  
  Make use of the RedNet Control software provided by Focusrite to:
  - Check synchronization status.
  - Confirm clock status ("Network Locked" indicator on the MP8R front panel and software interface).
  - Manage channel configurations and gain compensation features.

---

### 5. **Potential Challenges**

- **Mixed Protocol Management:**  
  Managing two synchronization protocols (NTP and PTP) simultaneously introduces complexity; clearly document settings.
- **Budget & Equipment:**  
  The need for specialized Grandmaster clock equipment may impact your budget.
- **Technical Knowledge:**  
  Familiarity with Dante Controller, network management, and synchronization technology is required.

---

### 6. **Benefits of the Hybrid Approach**

- **Accuracy:**  
  Audio synchronization remains precise (microsecond accuracy), ensuring the integrity of bioacoustic recordings.
- **Milestone Integration:**  
  Full compatibility with Milestone VMS through NTP, fulfilling their explicit synchronization requirement.
- **Scalability:**  
  Future expansions (more audio or video devices) remain straightforward and centrally manageable.

---

### 7. **Conclusion & Recommendation**

- While the hybrid synchronization solution is slightly more complex initially, it ensures:
  - Optimal synchronization accuracy for audio (via PTP/Dante).
  - Compliance with Milestone's NTP requirement for video.
  - Highly reliable operation, crucial for long-term bioacoustic monitoring projects.

Given the robust clocking and redundancy features of the **RedNet MP8R**, your choice to use this device positions your setup very effectively for professional-level synchronization and reliability.
