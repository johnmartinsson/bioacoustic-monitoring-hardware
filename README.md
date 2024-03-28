# Bioacoustic monitoring hardware

Great reference: [Choosing Equipment for Animal Bioacoustic Research](https://link.springer.com/chapter/10.1007/978-3-030-97540-1_2)

Quick research on available bioacoustic monitoring hardware for monitoring Guillemots in the Baltic Sea. The site has power and network readily available, and just needs microphones installed which collect audio. The microphone streams should in the best case be available over wifi.

- AudioMoth, ~1kSEK, https://www.openacousticdevices.info/audiomoth
- BAR-LT, ~6.5kSEK, https://www.frontierlabs.com.au/
- SONG METER SM4, ~10kSEK, https://www.frontierlabs.com.au/
- CHORUS, ~7kSEK, https://www.titley-scientific.com/product/chorus/
- Swift, ~3.5kSEK, https://www.birds.cornell.edu/ccb/swift/


## Network of bioacoustic monitoring hardware

The AudioMoth is farily cheap, samples at frequencies up to 384kHz, and is fully open source and configurable. Let's start exploring this option.

My current idea is that a good way forward would be to buy a couple of AudioMoths, turn them into USB Microphones, and connect them to a USB hub which is then connected to a Raspberry Pi. The Raspberry Pi will handle the streams of data and upload them to the central server.

### AudioMoth USB Microphone
- https://www.openacousticdevices.info/usb-microphone
- https://github.com/OpenAcousticDevices/Application-Notes/blob/master/Using_the_AudioMoth_Live_App_with_the_AudioMoth_USB_Microphone/Using_the_AudioMoth_Live_App_with_the_AudioMoth_USB_Microphone.pdf
