Given your study objectives—monitoring a **Guillemot colony** at a **cliffside location** with **power and ethernet available**—these are the most important considerations and recommendations for proceeding effectively:

---

# **Key Considerations for Equipment Selection**

#### **1. Dynamic Range and Bit Depth**
- **Why it’s important**: Guillemots can produce very loud calls close to the microphone, but you also want to capture quieter sounds from the colony.
- **Action**: Choose a **24-bit recorder** to maximize the dynamic range (~144 dB in theory, but practically around 110–120 dB). This will help preserve both the loud calls and subtle colony sounds.
- **Alternative**: Consider a **32-bit floating point** recorder if available, as it can automatically adjust gain without clipping loud calls or losing quiet sounds.

#### **2. Microphone Sensitivity and Self-Noise**
- **Why it’s important**: To capture the fine details of distant colony sounds, the microphone must have **low self-noise**.
- **Action**: Use **high-quality condenser microphones** (such as measurement microphones or high-end shotgun microphones with self-noise below ~10 dB(A)).
- **Example**: The **Rode NT1A (5.5 dB(A) self-noise) or Sennheiser MKH 8020 (10 dB(A) self-noise)** could be suitable options.

#### **3. Directionality and Placement**
- **Why it’s important**: You need to balance capturing **direct** (loud) sounds from close Guillemots while still picking up the **ambient** sounds from the colony.
- **Action**:
  - Use **stereo microphones** to capture spatial information.
  - Use a **cardioid or supercardioid microphone** to balance nearby and distant sounds while reducing noise from the sea/wind.
  - **Position microphones higher than the birds** to avoid direct strikes or pecking.

#### **4. Environmental Durability**
- **Why it’s important**: The **Baltic Sea cliffside** is an exposed, humid, and potentially windy environment.
- **Action**:
  - Use **weatherproof housings** (such as **IP-rated enclosures**) to protect microphones and recorders.
  - **Foam windscreens** and **furry covers** to prevent wind distortion.
  - **Corrosion-resistant connectors** (e.g., XLR with weatherproof sealing).

#### **5. Sampling Rate and Bandwidth**
- **Why it’s important**: While Guillemots primarily vocalize within human-audible frequencies, you may need flexibility for **detailed spectrogram analysis**.
- **Action**:
  - Use **48 kHz or 96 kHz sampling rate** (avoid 44.1 kHz as it’s optimized for music).
  - If monitoring ultrasonic elements (e.g., potential insect or echolocation activity), use **192 kHz**.

#### **6. Data Storage and Ethernet Integration**
- **Why it’s important**: Continuous, long-term recording will generate **large amounts of data**.
- **Action**:
  - **Use networked recording solutions** (e.g., **PoE microphones or network-attached recorders**).
  - **Store audio on an on-site NAS or dedicated server** for remote access.
  - **Automate uploads** to a cloud-based storage system (if remote analysis is needed).
  - Consider **real-time streaming** with web-based audio monitoring.

---

### **Suggested Plan for Deployment**

#### **Step 1: Choose and Test Equipment in a Controlled Environment**
- **Purchase or rent** candidate microphones and a recorder.
- **Test different configurations** (e.g., shotgun vs. cardioid vs. omnidirectional, stereo vs. mono).
- **Check for self-noise and wind performance** before field deployment.

#### **Step 2: Install Microphones on the Cliffs**
- Use **multiple microphone placements**:
  - **1–2 directional microphones** pointed at key nesting areas.
  - **1–2 omnidirectional microphones** to capture colony-wide ambient sounds.
  - **Stereo pair** for immersive soundscape recording.
- Secure **weatherproofing and wind protection**.

#### **Step 3: Configure Network and Data Storage**
- Set up an **on-site recording server or NAS**.
- Enable **remote access** to monitor data collection in real-time.
- Implement **scheduled backups** to a remote/cloud server.

#### **Step 4: Calibrate and Monitor**
- Use a **calibrated reference sound source** (such as a test tone) to document system sensitivity.
- Monitor recordings for **gain settings, clipping, and data integrity**.
- Adjust positioning if necessary.

#### **Step 5: Automate and Maintain**
- Use **automated scripts** for file management (e.g., compression, tagging).
- **Check microphone health regularly** (moisture buildup, damage from birds).
- Periodically **review and optimize** gain levels.

---

### **Final Notes**
- **Priority:** Low-noise microphones with wide dynamic range to handle both loud calls and distant colony sounds.
- **Redundancy:** Use multiple microphones to ensure good coverage.
- **Longevity:** Protect against wind, moisture, and corrosion.
- **Network:** Leverage Ethernet for **real-time monitoring** and **automatic storage management**.

By following this structured approach, you can ensure high-quality long-term recordings while minimizing equipment failures and data loss. Would you like specific microphone/recorder model recommendations based on budget constraints?


# **📌 Final Verdict: PoE-Based Power Setup for Continuous Operation**
Since **PoE is the preferred power source**, along with access to **12V and 230V power**, here’s the **final, optimized solution** for **4-5 months of uninterrupted Guillemot monitoring** using the **Annuncicom 200, MKE 600, and AT8010**.

---

## **🔹 Final Equipment List**
| **Component** | **Function** | **Power Source** | **Additional Notes** |
|--------------|-------------|------------------|---------------------|
| **Annuncicom 200** | **Main ADC & network streamer** | ✅ **PoE (48V)** | Also supports **16-30V DC**, but PoE is best. |
| **Sennheiser MKE 600** | **Directional mic for individual birds** | ✅ **PoE-fed Phantom Power Injector (48V)** | Alternative: Use **12V-230V Phantom Power Supply**. |
| **Audio-Technica AT8010** | **Omnidirectional mic for colony sounds** | ✅ **PoE-fed Phantom Power Injector (48V)** | Alternative: Use **12V-230V Phantom Power Supply**. |
| **PoE Network Switch (48V, IEEE 802.3af/at)** | **Main power source for Annuncicom 200 & Mic Power Injectors** | ✅ **230V AC → PoE** | Industrial-grade, reliable switch. |
| **PoE Phantom Power Injector (e.g., Radial StageBug SB-48, Audio-Technica AT8202)** | **Provides 48V Phantom Power for Mics** | ✅ **PoE-powered (48V)** | Alternative: Use **12V DC or 230V AC phantom power supply**. |
| **Cat6/Cat7 Ethernet Cable (Outdoor-Rated)** | **Data + Power Transmission** | ✅ **From PoE switch** | Use **shielded cables for durability** in outdoor environments. |
| **Weatherproof Mic Housing** | **Protects microphones from rain & wind** | ✅ **Custom Enclosures or Commercial Units** | Includes **windscreens & mounting hardware**. |

---

## **🔹 Key Considerations**
### **1️⃣ Power Management**
- **PoE is the best option** → It provides **both power and network connectivity**, **simplifying installation**.
- **Ensure the PoE switch supports 48V IEEE 802.3af/at standard.**
- **Backup Option:** If PoE fails, **12V DC or 230V AC** can power **Annuncicom 200 + Phantom Power Supply**.

### **2️⃣ Microphone Powering & Connectivity**
- The **MKE 600 and AT8010 require Phantom Power (48V)**.
- The **PoE switch alone does NOT provide Phantom Power** → Need **PoE-powered Phantom Power Injectors**.
- **Alternative:** Use **a 230V or 12V Phantom Power Supply** if PoE injectors are unavailable.

### **3️⃣ Environmental Protection**
- **Microphones must be housed in weatherproof enclosures**.
- **Wind noise reduction** → Use **furry windshields + shock mounts**.
- **Annuncicom 200 should be installed in a sheltered area** to avoid moisture and temperature extremes.

### **4️⃣ Network & Storage**
- **Ensure network stability** → If PoE switch is on-site, it should have a **UPS (Uninterruptible Power Supply)** to handle power outages.
- **Data Storage:** Annuncicom **streams audio over IP**, so **recording must be handled remotely**.
- If **local storage is needed**, consider a **NAS or Edge Recording Device**.

---

## **🔹 Final Action Plan**
✅ **Order Annuncicom 200** (Power via **PoE Switch**)  
✅ **Order MKE 600 (Directional) + AT8010 (Omni)**  
✅ **Order PoE Switch (48V, IEEE 802.3af/at)**  
✅ **Order PoE Phantom Power Injectors (48V) for Mics**  
✅ **Use Outdoor-Rated Ethernet Cable (Cat6/Cat7, Shielded)**  
✅ **Install Weatherproof Microphone Enclosures + Wind Protection**  
✅ **Verify Remote Network Storage or Recording Solution**  
✅ **Test the full system before field deployment**  

---

## **🏆 Final Verdict: Fully PoE-Based, Reliable, and Low-Maintenance**
- **No need for battery replacements** – everything runs from **PoE**.
- **Annuncicom 200 + PoE Switch → Single Cable for Power & Data**.
- **Microphones powered via PoE-fed Phantom Power Injectors** (alternative: 12V/230V Phantom Power).
- **Weatherproof & Long-Term Deployment Ready**.

🚀 **This setup ensures a robust, uninterrupted bioacoustic monitoring system for your Guillemot colony.**  
Would you like **specific product recommendations for PoE switches, injectors, or enclosures**?


# Milestone Considerations
1. **Drivers in Milestone XProtect**  
   - Responsible for the “handshake” between XProtect and cameras, controlling PTZ, video streaming, and audio.

2. **Generic Drivers (ONVIF / Universal)**  
   - Allow adding devices not officially supported.
   - May result in losing advanced features (e.g., analytics, camera-side motion detection).

3. **Compatibility Requirements**  
   - The camera must be able to output RTSP or ONVIF streams.
   - Must use a codec supported by Milestone (e.g., G.711 for audio, H.264 for video).

4. **Higher Audio Quality**  
   - AAC support is available only in paid Milestone editions (Professional+, Expert, Corporate).
   - Essential+ typically limits audio to G.711.

5. **Testing and Validation**  
   - Always test your device in XProtect Management Client to ensure video/audio work correctly.
   - Verify video quality, audio synchronization, and any critical features.

6. **Decision Making**  
   - If high-quality audio or advanced features are essential, consider:
     - Choosing an officially supported camera, or
     - Upgrading to a different XProtect edition that includes AAC or other needed capabilities.
