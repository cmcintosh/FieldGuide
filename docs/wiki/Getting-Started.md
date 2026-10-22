# Getting started

Install Python 3.10+, clone FieldGuide and run:

```bash
python app.py check
python app.py import examples/sample-content.jsonl
python app.py serve
```

Open http://127.0.0.1:8765 on the same device. Ask “How should I organize a digital preparedness library?” With no model configured the app shows excerpts rather than pretending to generate an answer.

Use `py` on Windows or `python3` on Linux/Pi if needed. See the [installation guide](https://github.com/cmcintosh/FieldGuide/blob/main/docs/installation.md) for Android Termux and llama.cpp. Store Android data/models inside Termux's private home directory. A separate native nearby-transfer companion is available through the Android CI artifact; see [Native Android](Native-Android.md). It does not yet embed the knowledge/maps app.

The three sample documents are original demonstrations, not a loaded emergency or medical library. Import appropriate reference material before relying on the collection. Back up through the Backup tab or `python app.py backup snapshot.json`.
