# Native Android Bluetooth and Wi-Fi companion

FieldGuide now includes a native **FieldGuide Nearby** companion under `android/`. It implements Bluetooth Classic RFCOMM discovery/listening/sending, Wi-Fi Direct discovery/group connections, local-only hotspot control and existing-LAN TCP exchange. It uses Android framework APIs with runtime permissions and user-controlled connections.

The companion imports an exported selected-share file or composes a message as a document. Receivers validate and review incoming content before accepting it. Accepted files can be exported and imported into the Python library. It does not yet embed the LLM/map application, replace Termux, implement BLE/mesh or provide a background transfer service.

The [Android guide](https://github.com/cmcintosh/FieldGuide/blob/main/android/README.md) covers installation, permissions, Bluetooth, group roles, hotspots and Pi/laptop exchange. The [FGT1 protocol](https://github.com/cmcintosh/FieldGuide/blob/main/docs/transport-protocol.md) specifies the shared stream format.

A successful **Android companion** Actions run publishes `fieldguide-nearby-debug-apk`. Compile/lint and protocol tests are separate from physical device tests. Radio behavior must be checked on two actual phones before claiming device support.
