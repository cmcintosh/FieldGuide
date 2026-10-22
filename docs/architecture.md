# FieldGuide architecture

FieldGuide is an original GPL-2.0-only project, inspired by the offline knowledge use case. It does not fork NOMAD or embed its Apache-2.0 code. The current application uses the Python standard library and local browser assets; the eventual native Android shell is a separate milestone.

## Repository structure

| Path | Responsibility |
|---|---|
| `src/fieldguide/storage.py` | SQLite schema, document chunks, FTS5/BM25, model request, household records and backups |
| `src/fieldguide/server.py` | Local HTTP interface, input boundaries, peer endpoints and CLI |
| `src/fieldguide/maps.py` | Read-only raster MBTiles metadata/tiles and TMS conversion |
| `src/fieldguide/peer.py` | Selected bundles, short-lived offers, integrity checks, idempotent merge and waypoint validation |
| `src/fieldguide/audio.py` | Experimental framed FSK WAV encoding/decoding |
| `src/fieldguide/link.py` | Bounded FGT1 stream framing and one-shot TCP bridge |
| `android/` | Native nearby companion: radio discovery, links, bundle review and file handoff |
| `src/fieldguide/static` | Local HTML/CSS/JavaScript; no CDN assets |
| `tests` | Storage, HTTP, maps, peer and synthesized-audio verification |
| `examples` | Original demonstration documents |
| `docs/wiki` | Versioned wiki source pages |

## RAG

A question goes through disk-backed lexical retrieval, weak-match filtering and bounded excerpt selection. Up to four excerpts go to a separately installed numeric-loopback OpenAI-compatible model endpoint. Proxy forwarding, redirects and public model URLs are disabled. Only one generation request runs at once. Missing/busy/unavailable model handling retains original sources. Citation checking validates identifiers rather than factual entailment.

The first quality candidates are quantized post-trained Qwen3.5-2B and 0.8B, tested with a compatible llama.cpp build. These are candidates, not validated device recommendations. A phone does not need another host once its local runtime and assets are installed. Initial targets are 8 GB ARM64 Android/Pi 5 and a 16 GB laptop; actual memory and latency remain to be measured.

Next retrieval work: actual tokenizer-aware budgeting, small on-device query embeddings, offline-prepared document vectors, topic shards, hybrid ranking and a human-reviewed evaluation dataset. Large reference archives should stay compressed (ZIM/libzim search) rather than immediately duplicating all Wikipedia into a dense index. ZIM/PDF and semantic ingestion are not implemented yet.

## Maps and local records

Raster MBTiles files remain separate, read-only assets. The browser requests only local tile URLs. No external fallback, downloader, geocoder or routing graph is used. Waypoints live in the application database and have stable UUIDs for backup/share deduplication. An imported map's attribution remains visible. Browser device location is an explicit action and is never automatically transmitted.

Original reference packs should eventually be immutable, versioned and verified. Private notes, inventory and progress must remain separate from public packs. Typed arithmetic should calculate supply totals; the model can explain the result but should not invent inputs or execute arbitrary SQL.

## Peer exchange

Both peers run their own local workspace. A manual LAN/hotspot link supplies IP connectivity. When hosting is enabled, token-gated read-only peer routes expose a selected immutable snapshot for 15 minutes. Normal private workspace routes remain loopback-only. The receiver checks size and SHA-256 before a transactional merge. The small-record protocol excludes household inventory, notes, maps and models; it is not continuous sync.

Current HTTP bearer codes are a development transport, not authenticated encryption. Native Android transport adapters should implement Wi-Fi Direct/hotspot/Bluetooth discovery, runtime permissions, session identity, encrypted transfer, bounded/resumable chunks and explicit content acceptance. Wi-Fi Direct groups are not a multi-hop mesh. Bluetooth file exchange through the OS is available separately from an in-app socket adapter.

## Acoustic exchange

The original codec offers explicit short-text WAV generation and decoding, with 20.5/21.5 kHz carriers and an audible diagnostic profile. It uses framing, preamble alignment and CRC; it has no error correction, encryption, live microphone capture or automatic importing. Software loopbacks and synthesized-noise tests are not physical-link validation. Use the hardware evaluation plan before promising range, reliability or inaudibility.

## Delivery stages

1. Delivered: package, local retrieval/model adapter, basic records, raster map viewer, selected peer exchange, experimental WAV codec, docs and tests.
2. Measure actual Android/Pi models, location/map behavior, real local links and acoustic hardware.
3. Improve content ingestion and retrieval; publish reproducible packs and evaluation results.
4. Package a native Android app with lifecycle/permission controls and native inference.
5. Add secure native radios, resumable large-pack transfer and robust acoustic capture/transport.
6. Add vector maps, POIs/GPX, education and appliance installation/updates. Scope navigation separately.

All runtime assets must work after disconnecting and rebooting. Content/model/map licensing is independent of the project's GPLv2 source license. See the wiki for protocols, limits and primary references.

## Native transport companion update

The Android companion implements secure RFCOMM sockets, Wi-Fi Direct peer/group control and local-only hotspot requests. One operation at a time owns bounded sockets; cancellation closes blocking resources. Files use the same selected-share JSON envelope with independent FGT1 framing. Runtime permission denial is handled in the Activity. Incoming content needs explicit review/acceptance. This is not yet a complete native RAG/maps app, a mesh or a background service. See `android/README.md` for the integration boundary and hardware validation requirements.
