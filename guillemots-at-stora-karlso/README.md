## In Summary

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
