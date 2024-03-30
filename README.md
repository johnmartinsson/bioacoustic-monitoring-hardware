# Bioacoustic monitoring hardware

Great reference: [Choosing Equipment for Animal Bioacoustic Research](https://link.springer.com/chapter/10.1007/978-3-030-97540-1_2)

Quick research on available bioacoustic monitoring hardware for monitoring Guillemots in the Baltic Sea. The site has power and network readily available, and just needs microphones installed which collect audio. The microphone streams should in the best case be available over wifi.

- AudioMoth, ~1kSEK (down to 0.6kSEK if Grouper Deal), https://www.openacousticdevices.info/audiomoth
- BAR-LT, ~6.5kSEK, https://www.frontierlabs.com.au/
- SONG METER SM4, ~10kSEK, https://www.frontierlabs.com.au/
- CHORUS, ~7kSEK, https://www.titley-scientific.com/product/chorus/
- Swift, ~3.5kSEK, https://www.birds.cornell.edu/ccb/swift/

I do not yet know if any of these support wifi out of the box.


## Network of bioacoustic monitoring hardware

The AudioMoth is farily cheap, samples at high frequencies, and is fully open source and configurable. Let's start exploring this option.

My current idea is that we

- buy a couple of AudioMoth USB Microphones, and
- connect them to a to a Raspberry Pi or similar.

The Raspberry Pi will collect the streams of data and upload them to the central server.

E.g., buy through this grouper campaing:

- https://www.openacousticdevices.info/purchase

### AudioMoth USB Microphone

Any AudioMoth can be turned into a USB Microphone:
- https://www.openacousticdevices.info/usb-microphone
- https://github.com/OpenAcousticDevices/Application-Notes/blob/master/Using_the_AudioMoth_Live_App_with_the_AudioMoth_USB_Microphone/Using_the_AudioMoth_Live_App_with_the_AudioMoth_USB_Microphone.pdf

Performance test
- https://github.com/kitzeslab/audiomoth-performance
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10256106/

Specification sheet
- AudioMoth 1.2.0 uses the SPU0410LR5H - [datasheet](https://media.digikey.com/pdf/Data%20Sheets/Knowles%20Acoustics%20PDFs/SPU0410LR5H-QB_RevH_3-27-13.pdf)
- https://www.openacousticdevices.info/support/device-support/calibration-curve-for-audiomoth

### Other Microphones

- https://www.grasacoustics.com/products/special-microphone/outdoor-microphones/product/202-41cn (Tip from Holger Klink)

### Network

- https://www.barix.com/product/instreamers/ (Tip from Holger Klink)

