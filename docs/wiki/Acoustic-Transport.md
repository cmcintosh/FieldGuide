# Experimental acoustic transport

Audio creates a deliberate communication path between otherwise disconnected devices. FieldGuide's experiment encodes short user-selected text into PCM WAV and decodes recordings into displayed text. It does not listen in the background, automatically play sounds, execute received content or import received records.

## Implemented waveform protocol

| Parameter | Value |
|---|---|
| Format | Mono signed 16-bit PCM WAV, 48,000 samples/second |
| Ultrasonic carrier candidates | 20,500 and 21,500 Hz |
| Audible diagnostic carriers | 1,700 and 2,700 Hz |
| Modulation | Binary FSK; 480 samples/symbol, nominal 100 bits/second before framing |
| Frame | Eight 0xAA preamble bytes, `FG02`, 16-bit big-endian payload length, UTF-8 text, CRC32 |
| Payload | 1–160 UTF-8 bytes; text only |
| Decoder | Goertzel tone comparison, phase candidates, preamble search, CRC rejection |
| Unimplemented | Error correction, retransmission/ACK, encryption, signatures, live capture, clock-drift compensation |

The nominal symbol rate is a format parameter, not measured usable hardware throughput. A 160-byte frame takes approximately 14.26 seconds including framing/padding. This is unsuitable for map archives, models and large documents.

## Try it

In the Audio link tab, choose a profile and enter text. Create WAV exposes a player and download link; playback requires another explicit action. On the receiving device, record mono PCM 16-bit WAV at 48 kHz using an audio tool that preserves the relevant frequencies, then upload the WAV and decode it using the same profile. Live browser microphone capture is not implemented.

CLI from an installed package:

```bash
fieldguide-audio encode message.wav --text "Meet at north gate" --profile ultrasonic
fieldguide-audio decode recording.wav --profile ultrasonic
```

From a source checkout, use `PYTHONPATH=src python -m fieldguide.audio ...`, or install the package first. The encoder refuses to overwrite an existing output file.

## Hardware reality

Frequencies above the commonly cited upper human hearing boundary are not guaranteed to be inaudible in practice: devices can generate audible artifacts and people vary. Consumer speakers/microphones, codecs and voice-processing filters may strongly attenuate these carriers. Avoid compressed speech recordings and disable voice processing where the recording tool supports it. A 48 kHz sample rate provides mathematical bandwidth, not a guarantee that the physical hardware passes 21.5 kHz. Start with the audible diagnostic profile and then measure the ultrasonic profile on each hardware pair; do not compensate for failure by automatically increasing volume.

No physical audio link, range, reliability, safety level or universal inaudibility has been established. Tests cover synthesized WAV round trips, artificial noise, timing offset and checksum rejection only. CRC is not authentication or encryption. Anyone within acoustic range may be able to hear/decode transmitted data; keep sensitive payloads out of this prototype.

The implementation is original and GPL-2.0-only. It is not compatible with ggwave. [ggwave](https://github.com/ggerganov/ggwave) is a useful MIT-licensed research reference with error correction; its documented “ultrasonic” profile occupies 15–19.5 kHz and therefore does not satisfy a strict above-20-kHz requirement.

Next: actual frequency-response tests, optional raw capture/playback adapters, framing with authenticated sessions, error correction, retries and payload review before import. Automatic covert transmission is outside the product design.
