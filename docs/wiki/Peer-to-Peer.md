# Peer-to-peer exchange

## Current Wi-Fi / hotspot workflow

1. Run FieldGuide on both devices. Manually join the same private Wi-Fi network or connect one device to the other's hotspot. Internet is not needed; some hotspots, VPNs or client-isolation settings can block device-to-device traffic.
2. On the sender, start `python app.py serve --host 0.0.0.0`. Open http://127.0.0.1:8765 on that device.
3. In Nearby sharing, select individual documents and waypoints and create a share. The immutable snapshot gets a random code, expires after 15 minutes, and can be revoked. A new share replaces the previous offer.
4. On the receiver's **own local** FieldGuide interface, enter `http://SENDER_PRIVATE_IPV4:8765` and the complete code, then receive.
5. The receiver downloads the manifest and bundle, checks size/SHA-256 and imports transactionally. Document/waypoint repeats are deduplicated. It has its own stored copy afterward.

Only selected documents and waypoints are exposed. Inventory, private notes, map files and models are excluded. The private workspace remains loopback-only, even while peer exchange listens on the LAN. A code is reusable until revoked/expired; this is not a one-use pairing protocol. There is no background sync or automatic discovery.

The development transport is plain HTTP with a bearer code. A checksum detects corruption, not impersonation or tampering by an active network attacker. The protocol does not implement encrypted transport, mutual identity verification or conflict resolution. Use an appropriate private test link; production work needs authenticated/encrypted sessions.

## Bluetooth file transfer today

Export selected records as a JSON file, transfer it using the operating system's file-sharing facility (Bluetooth where available), and use Import shared file on the receiver. That is file transfer outside FieldGuide, not an in-app Bluetooth socket connection.

## Native Android companion status

| Transport | Intended role | Current status |
|---|---|---|
| Wi-Fi Direct | Direct Android links without a router; group owner topology | Native discovery/group/connection code and TCP transfer implemented; hardware validation pending |
| Local-only hotspot | Share with nearby Android/Pi/laptops without internet | Native creation/credentials/stop implemented; joining through OS settings |
| Bluetooth Classic RFCOMM | Small messages and selected records | Native discovery, paired sockets and one-shot selected-bundle transfer implemented; hardware validation pending |
| BLE | Optional discovery/pairing metadata | Not implemented; avoid large pack transfers |
| Acoustic | Small explicit text payloads; potential pairing hints | Experimental WAV codec; see acoustic page |

Use Android's native APIs with runtime permissions and lifecycle handling. Wi-Fi Direct groups are not a general multi-hop mesh. A shared transfer envelope should sit above each transport, with chunking, resumability, authentication and recipient confirmation. Large maps/models belong on Wi-Fi; short messages and pairing data are better audio/Bluetooth candidates.

Primary references: [Wi-Fi Direct](https://developer.android.com/develop/connectivity/wifi/wifip2p), [Bluetooth data](https://developer.android.com/develop/connectivity/bluetooth/transfer-data), [local-only hotspot](https://developer.android.com/develop/connectivity/wifi/localonlyhotspot).

The [native companion guide](Native-Android.md) covers the app and debug APK. Its FGT1 stream protocol on port 43721 is distinct from the HTTP/share-code workflow on port 8765. Full native LLM/maps integration is still planned.
