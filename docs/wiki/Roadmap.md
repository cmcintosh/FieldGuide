# Roadmap

## Delivered foundation

- Local lexical retrieval, model adapter, source reading and basic household records.
- Raster MBTiles viewer, saved waypoints and backups.
- Selected-record local Wi-Fi transfers and file exchange.
- Experimental framed audio WAV codec, structured repository, tests and CI.
- Native Android nearby companion, Bluetooth/Wi-Fi Direct/hotspot adapters and Python FGT1 bridge.

## Next implementation stages

1. Validate actual phone/Pi models, maps, local links and audio hardware. Record a tested-device matrix.
2. Improve RAG with tokenizer-aware budgeting, curated packs, semantic retrieval, PDF source locations and evaluation datasets.
3. Extend the native nearby companion into a complete Android knowledge/maps app with JNI inference and managed storage.
4. Validate the implemented Android radios on devices, then add authenticated/encrypted sessions and resumable transfers.
5. Add vector maps, POIs, tracks and GPX; scope routing separately. Implement large map/content-pack transfer over Wi-Fi.
6. Improve acoustic robustness with capture/playback adapters, real-device calibration, error correction and retransmission. Keep user-visible payload/recipient controls.
7. Add ZIM libraries, offline courses and appliance installation/updates with rollback.

No release date or hardware performance is promised before measurement. A generated native app skeleton or an untested radio adapter does not satisfy the corresponding milestone.
