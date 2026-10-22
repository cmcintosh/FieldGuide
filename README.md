# FieldGuide

An offline knowledge and preparedness toolkit for laptops, Raspberry Pi and Android development environments. Search local references, ask a separately installed local model, view installed offline maps, and exchange explicitly selected records with another device.

**Development preview 0.3 · GPL-2.0-only · Python 3.10+ · no Python runtime dependencies**

## Current capabilities

| Capability | Implemented now | Limits |
|---|---|---|
| Knowledge and RAG | Text/Markdown/JSONL import, SQLite BM25 retrieval, original sources, local model adapter | Model weights separate; no embeddings/PDF/ZIM ingestion yet |
| Offline maps | Local raster MBTiles, pan/zoom, attribution, saved waypoints, browser location request | Map files separate; no vector PMTiles/PBF rendering, geocoding or routing |
| Local peer exchange | Python HTTP shares plus a native Android Bluetooth/Wi-Fi Direct/hotspot companion and TCP bridge | Native radios require device validation; no BLE/mesh or background service |
| Audio experiment | Explicit WAV encoding/playback and WAV decoding; 20.5/21.5 kHz or audible test tones | Short text, 160 UTF-8 bytes; no live microphone capture or proven hardware link |
| Household records | Add supply entries, entered-calorie totals, notes, backup/restore | No full consumption/nutrition planner or encrypted storage |

This is original software inspired by the offline knowledge use case. It is not a Project NOMAD fork and includes no NOMAD code, third-party content packs or model weights. The knowledge/maps app currently uses Termux on Android. A separate native **FieldGuide Nearby** companion now exchanges selected records over Bluetooth, Wi-Fi Direct and local Wi-Fi; it does not yet embed the LLM/maps UI. See [Android setup and APK builds](android/README.md).

## Quick start

From a checkout, no pip install is required:

```bash
git clone https://github.com/cmcintosh/FieldGuide.git
cd FieldGuide
python app.py import examples/sample-content.jsonl
python app.py serve
```

On Windows use `py` instead of `python` if needed; on Linux/Pi use `python3`. Open **http://127.0.0.1:8765** on the same device. Source search works without an LLM.

Optional package installation:

```bash
python -m pip install -e .
fieldguide serve
```

Local AI example, after downloading the model and starting Ollama:

```bash
python app.py serve --endpoint http://127.0.0.1:11434/v1/chat/completions --model qwen3.5:2b
```

Offline map example:

```bash
python app.py serve --map /path/to/region.mbtiles
```

Repeat `--map` for more regions. Use raster PNG/JPEG/WebP MBTiles in standard TMS format. No map downloader or geographic data is bundled.

For peer hosting, start with `--host 0.0.0.0`, open the **local** interface and choose **Nearby sharing**. Only the token-gated peer endpoints become accessible from another device; its private workspace remains local-only. Both devices run their own instance.

## Documentation

Start with the [versioned wiki pages](docs/wiki/Home.md), [installation guide](docs/installation.md) and [architecture](docs/architecture.md).

- [Offline maps](docs/wiki/Offline-Maps.md)
- [Peer-to-peer exchange and Android transports](docs/wiki/Peer-to-Peer.md)
- [Native Android companion and APK](android/README.md)
- [Shared Bluetooth/TCP protocol](docs/transport-protocol.md)
- [Experimental acoustic transfer](docs/wiki/Acoustic-Transport.md)
- [RAG and models](docs/wiki/RAG-and-Models.md)
- [Hardware validation](docs/wiki/Hardware-Testing.md)
- [Roadmap](docs/wiki/Roadmap.md)
- [License and third-party assets](THIRD_PARTY.md)

`docs/wiki` is the documentation source of truth. These files are wiki-ready Markdown; they do not by themselves publish GitHub's separately managed Wiki. See [wiki publication instructions](docs/wiki/Publishing-the-Wiki.md).

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
node --check src/fieldguide/static/app.js
node --check src/fieldguide/static/map.js
```

Code lives in `src/fieldguide`, tests in `tests`, example content in `examples`, and documentation in `docs`. Models, map archives, databases and audio recordings are excluded from git. CI checks Python 3.10, 3.12 and 3.13.

Tests cover software behavior and synthesized audio. They do not establish Android/Pi compatibility, LLM answer quality or a working speaker/microphone connection. See [validation status](docs/validation.md).

## License

Copyright (C) 2026 FieldGuide contributors. FieldGuide is free software under the **GNU General Public License version 2 only**, SPDX `GPL-2.0-only`. See [LICENSE](LICENSE). This program comes with no warranty. External model weights, maps and reference material retain their own licenses.
