# Installation and running

## Source checkout: Windows, Linux and macOS

Install Python 3.10+ with SQLite FTS5, clone the repository, then:

```bash
python app.py check
python app.py import examples/sample-content.jsonl
python app.py serve
```

Use `py` on Windows or `python3` on Linux where needed. Open http://127.0.0.1:8765 on the same device. Leave the terminal running; Ctrl+C stops it. Imports are idempotent for exact text/metadata duplicates. Model weights and real reference/map packs are not included.

Optional installation provides the `fieldguide` and `fieldguide-audio` commands:

```bash
python -m pip install -e .
```

## Raspberry Pi

Use a 64-bit OS; Pi 5 with 8 GB, cooling and SSD is the initial target. Install Python and git using the OS package manager, then use the source-checkout steps. No Pi hardware execution has been verified here.

To build a recent compatible llama.cpp runtime while online:

```bash
sudo apt update
sudo apt install python3 git cmake build-essential
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_OPENMP=OFF
cmake --build build --config Release -j 2 --target llama-server
```

Obtain a licensed, post-trained Q4 GGUF compatible with that build and place it in `models/assistant.gguf`. A text-only deployment does not need a vision projector. From the llama.cpp directory:

```bash
./build/bin/llama-server -m models/assistant.gguf --alias fieldguide --host 127.0.0.1 --port 8081 -c 4096 -t 4 -np 1
```

In another terminal, from FieldGuide:

```bash
python3 app.py serve --endpoint http://127.0.0.1:8081/v1/chat/completions --model fieldguide
```

Record/pin the model hash and runtime commit after testing. New model formats can require updated llama.cpp versions. Short contexts and one generation at a time are starting configurations, not measured performance guarantees.

## Android knowledge app (Termux) and native nearby companion

For native Bluetooth/Wi-Fi Direct/hotspot exchange, build/install the separate app described in [android/README.md](../android/README.md). Its Actions artifact contains a debug APK. The following Termux setup runs the knowledge/maps application; the companion does not yet embed it.

### Termux setup

This is not a native APK. Install a supported Termux build from its [official installation instructions](https://github.com/termux/termux-app#installation). Use an ARM64 device and store the checkout, databases and model inside Termux's private home directory. For the 2B candidate start with an 8 GB device; validate real memory and thermal behavior.

```bash
pkg update
pkg install python git cmake clang make libandroid-spawn
git clone https://github.com/cmcintosh/FieldGuide.git
cd FieldGuide
python app.py import examples/sample-content.jsonl
python app.py serve
```

Open http://127.0.0.1:8765 in the phone's browser. For a local model, build llama.cpp in a separate directory using the CMake commands above, start its server, then start FieldGuide with the loopback endpoint. See [llama.cpp Android documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md). Android may kill background processes; test lifecycle and battery-optimization behavior on the actual device.

## Existing Ollama on a laptop

After downloading a local model while online, start Ollama and run:

```bash
python app.py serve --endpoint http://127.0.0.1:11434/v1/chat/completions --model qwen3.5:2b
```

Use local variants, not cloud-backed tags. The default package may be larger than a minimal text-only Q4 GGUF. The client restricts endpoints but cannot prevent a separate inference server from forwarding requests; configure that server for local inference.

## Maps, peers and audio

Pass `--map /path/region.mbtiles` for each raster MBTiles region. For incoming selected peer exchanges add `--host 0.0.0.0`; the private workspace still opens only on localhost. No OS hotspot or Bluetooth connection is created automatically. See the wiki pages for exact workflows.

The Audio link tab generates WAV and decodes uploaded PCM WAV recordings. An installed package also provides `fieldguide-audio encode file.wav --text "Message"` and `fieldguide-audio decode recording.wav`. No live microphone capture or physical-link success is promised.

## Backups

```bash
python app.py backup snapshot.json
python app.py restore snapshot.json --db data/recovered.sqlite3
python app.py serve --db data/recovered.sqlite3
```

Restore deduplicates documents/waypoints and appends notes/inventory. Recover into a fresh database for an exact snapshot; repeated merges duplicate the appended records. Map/model files are not in the backup. Data is not encrypted in this preview.

## Development checks

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The runtime has no third-party Python dependencies. Installation needs setuptools as the build tool. Device and UI limitations are recorded in `docs/validation.md`.
