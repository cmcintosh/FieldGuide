# FieldGuide Nearby — native Android companion

This GPL-2.0-only development app implements native nearby connections and exchanges FieldGuide selected-share files. It supports **Android 8.0 / API 26 and later** on devices with the relevant hardware. It is a companion to the Python knowledge/map app; it does not yet embed Python, maps, the LLM or the acoustic codec.

## Implemented transports

- **Bluetooth Classic:** discover or list paired devices, request short-lived discoverability, listen on a secure RFCOMM service, connect/pair through Android's UI, and send one selected bundle.
- **Wi-Fi Direct:** discover peers, request a connection, create a group, obtain the group owner's address and exchange the bundle over TCP.
- **Local-only hotspot:** ask Android to create a no-internet hotspot, display its system-generated credentials and stop it when finished. Other devices join using Android's Wi-Fi settings.
- **Existing local Wi-Fi:** listen or send to a numeric private IPv4 peer on port **43721**.

Radio APIs are implemented, but no physical phone-to-phone link has been verified here. OEM behavior, permissions, location settings on older devices, hotspot/client isolation and background process limits require device testing.

## Get/build the APK

The **Android companion** GitHub Actions workflow builds and lints a debug APK and publishes the `fieldguide-nearby-debug-apk` artifact. Download that artifact from a successful run and extract `app-debug.apk` for test installation on your devices. This is a debug-signed development build, not a store release.

For local development, open `android/` in a compatible Android Studio, or install JDK 17, Gradle 8.13 and Android SDK platform 36/build-tools 36.0.0:

```bash
gradle -p android :app:assembleDebug :app:lintDebug
```

No Gradle wrapper binary is vendored. The build uses AGP 8.13.2 and Android framework APIs without AndroidX or other application runtime libraries. APK output: `android/app/build/outputs/apk/debug/app-debug.apk`.

## Pick a payload

Export selected documents/waypoints from the Python app's **Nearby sharing → Export selected file**, then choose **Open selected-share JSON** in the companion. A full-library backup is a different format and is rejected. Alternatively, compose a title and field message; the companion wraps it as a document in the same selected-share format.

The bundle is capped at 7,000,000 bytes and 1,000 records. This is for selected records, not models or map packs. Incoming content is validated and presented for review; nothing is automatically imported or executed.

## Phone-to-phone Bluetooth

1. On the receiver, enable Bluetooth, tap **Receive one Bluetooth transfer**, then **Make discoverable for 120 seconds** if the sender cannot find it.
2. On the sender, load a selected-share file/message and use **Discover Bluetooth peers** or **show paired devices**.
3. Tap the intended recipient's **Send to…** entry. Complete Android's pairing dialog on both devices if shown.
4. The receiver reviews the verified bundle and taps **Accept received bundle to app storage** or rejects it. The sender's acknowledgement means the frame arrived, not that the recipient accepted/imported it.

One operation runs at a time. Starting a different transfer cancels the previous one. **Cancel current transfer** closes blocking sockets. Listeners wait up to two minutes; the overall operation budget is three minutes. Large/slow transfers can time out; resumption is not implemented.

## Phone-to-phone Wi-Fi Direct

1. Enable Wi-Fi on both phones. On the receiver tap **Host Wi-Fi Direct group and receive**.
2. On the sender tap **Discover Wi-Fi Direct peers**, choose the receiver and complete any Android connection prompt.
3. When connected, the sender's receiver-address field is filled from the group owner information. Tap **Send outgoing file over Wi-Fi**.
4. Review and accept/reject on the receiving phone. To reverse direction, put the other device into receive mode, enter its private IP if needed, and send explicitly.

Group creation/connection is asynchronous. A successful request is not a completed connection. Existing groups can cause `BUSY`; use **Disconnect Wi-Fi Direct group** and retry. Devices that do not expose Wi-Fi Direct are reported as unavailable. Some older Android versions require Location services enabled for discovery, even when the app does not derive location.

## Hotspot or existing Wi-Fi

1. Stop an active Wi-Fi Direct group if it conflicts with hotspot mode.
2. On the host, tap **Start local-only hotspot**. Join the displayed SSID from the other device using the displayed password. The hotspot has no upstream internet.
3. On the receiving device tap **Receive one Wi-Fi/TCP transfer**. On the sender enter the receiver's private IP, without a port, and tap **Send outgoing file over Wi-Fi**.
4. Stop the hotspot when done. The app shows local interface/IP candidates; it does not assume a fixed OEM gateway address. A VPN/cellular interface may also have a private address, so choose the relevant Wi-Fi interface.

The same send/listen flow works on an existing local Wi-Fi network when it allows clients to communicate. Joining a hotspot remains an OS-controlled step; no saved Wi-Fi credentials are modified silently.

## Exchange with a Pi/laptop

Both sides use the [FGT1 stream protocol](../docs/transport-protocol.md), distinct from the Python browser app's existing HTTP/share-code protocol on port 8765.

Receive a phone's outgoing bundle on a Pi/laptop:

```bash
python -m fieldguide.link listen --bind 0.0.0.0 --output received.json
```

On the phone, send over Wi-Fi to the Pi/laptop's private IP. The CLI saves one validated file, acknowledges delivery and exits. It refuses to overwrite an existing filename. Review it and import via the Python app's **Nearby sharing → Import shared file**.

Send an exported bundle to the phone while it is listening:

```bash
python -m fieldguide.link send --host 192.168.1.50 --input fieldguide-selected-share.json
```

Install the package first (`python -m pip install -e .`), or set `PYTHONPATH=src` when running modules directly from the checkout. The new `fieldguide-link` command is also installed. Receiver port is 43721 by default; the Python CLI exposes a port option for development, while the companion currently uses that fixed port.

## Review, persistence and privacy

Accept saves the last accepted bundle in private app storage. **Export last accepted bundle** writes a user-chosen JSON file through Android's document picker. Import that file into the Python app; the companion does not automatically modify a Termux database. The last outgoing and accepted bundles persist across restarts. Unaccepted pending content is not persisted.

Native receive/send is a bounded foreground development workflow, not a background mesh service. Keep the app open. Leaving/destroying the Activity closes its owned sockets/hotspot/group; the OS may kill background work. Discovery does not imply an authenticated FieldGuide peer. Bluetooth uses Android's paired secure RFCOMM API; raw TCP does not add application-level encryption or identity verification. SHA-256 detects corruption, not a malicious sender. End-to-end pairing/authentication, encryption, resumable large files and background operation remain planned.

Permissions are requested on the corresponding user action: Bluetooth Nearby permissions on Android 12+, Wi-Fi Nearby on Android 13+, and legacy location permission where needed. Denial is shown rather than bypassed. The app does not request microphone, camera, contacts or broad storage access.

## Testing

CI compiles an Android-independent Java `FrameCodec` test against the same golden frame as Python, then builds and lints the APK. Python tests include fragmented/truncated frames, invalid lengths, bad checksums, malformed bundles, real local TCP sockets and acknowledgements.

Compilation/lint and byte-level interoperability do not establish real radio behavior. Before calling a device supported, test two physical phones, permission denial, pairing cancellation, Wi-Fi Direct/group roles, hotspot creation, reversed direction, interrupted transfer, process destruction, malformed input and recipient rejection. Record device/OS and results in the hardware matrix.
