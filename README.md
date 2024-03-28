# Bioacoustic monitoring hardware
Quick research on available bioacoustic monitoring hardware for monitoring Guillemots in the Baltic Sea. The site has power and network readily available, and just needs microphones installed which collect audio. The microphone streams should in the best case be available over wifi.

- AudioMoth, ~1kSEK, https://www.openacousticdevices.info/audiomoth
- BAR-LT, ~6.5kSEK, https://www.frontierlabs.com.au/
- SONG METER SM4, ~10kSEK, https://www.frontierlabs.com.au/

Seems that all of these are made to stand of grid running on batteries for a long time and record audio onto an SD-card.

## Network of bioacoustic monitoring hardware

The AudioMoth is farily cheap, samples at frequencies up to 384kHz, and is fully open source and configurable. I think that this may be the way forward.

My current idea is that a good way forward would be to buy a couple of AudioMoths, turn them into USB Microphones, and connect them to a USB hub which is then connected to a Raspberry Pi. The Raspberry Pi will handle the streams of data and upload them to the central server.

### AudioMoth USB Microphone
- https://www.openacousticdevices.info/usb-microphone
- https://github.com/OpenAcousticDevices/Application-Notes/blob/master/Using_the_AudioMoth_Live_App_with_the_AudioMoth_USB_Microphone/Using_the_AudioMoth_Live_App_with_the_AudioMoth_USB_Microphone.pdf
