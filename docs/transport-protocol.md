# FGT1 bounded stream protocol

FGT1 carries an existing UTF-8 `field-library-share-v1` JSON bundle over a connected byte stream. Android secure Bluetooth RFCOMM and TCP use the same bytes. The existing HTTP bearer-code endpoints and acoustic FG02 frames are different protocols.

| Offset | Length | Value |
|---|---|---|
| 0 | 4 bytes | ASCII `FGT1` |
| 4 | 4 bytes | Unsigned big-endian payload byte count; 1–7,000,000 |
| 8 | 32 bytes | SHA-256 digest of the exact payload bytes |
| 40 | Declared count | UTF-8 selected-share JSON |

The receiver bounds the declared length before allocation, reads exactly that many bytes, verifies SHA-256 and validates the bundle. The payload must contain 1–1,000 documents/waypoints with required titles/text or waypoint coordinates. It then replies with one byte `0x06` and closes the connection. The sender treats a missing/different acknowledgement as failure. One connection carries one frame.

The acknowledgement means validated frame delivery. It does not authorize import or imply recipient acceptance. On Android, incoming content remains pending until the user accepts it; the Python listener saves a reviewed-later file and never imports it automatically. Python saves before acknowledgement. Android acknowledgement precedes user review and durable acceptance.

The protocol has no remote execution, identity exchange, encryption, replay prevention, resumable offsets or chunk acknowledgement. SHA-256 is an integrity checksum, not authentication. Bluetooth link security is provided by Android pairing, independently of this frame. Wi-Fi Direct/hotspot security is provided by the local link; raw TCP adds no application-layer security. Explicit peer selection and payload review remain necessary development controls.

## Compatibility fixture

`tests/fixtures/transport.json` is a fixed original bundle. `transport.frame.hex` is its exact frame. Python verifies the fixture and the independent Java self-test encodes/decodes against it. Both implementations reject malformed length, truncation and digest mismatch. The fixture is not generated during CI, so a change to only one implementation will fail interoperability checks.

## Bounds and lifetime

TCP connections use a ten-second connect timeout and thirty-second socket I/O timeout. Python listen waits two minutes by default. The Android controller closes an operation after three minutes and listens for an initial connection for at most two minutes. Bluetooth blocking operations are canceled by closing their sockets; there is no assumption that interrupting a worker thread alone unblocks them.

Future authenticated sessions and resumable transfers require a versioned protocol revision and compatibility tests. Do not silently redefine FGT1 framing or interpret untrusted payload fields as commands.
