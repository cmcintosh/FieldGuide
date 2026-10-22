# Validation — 22 October 2026

- Python 3.12 / SQLite FTS5: **50 automated tests pass locally**. The Tests workflow also runs Python 3.10, 3.12 and 3.13.
- Tests cover storage/import/backup, live local HTTP/model-client fixtures, raster maps, selected peer imports and the experimental audio codec.
- New FGT1 tests cover a fixed cross-language frame, fragmented reads, protocol/length/digest/truncation rejection, real local TCP delivery/acknowledgement and refusal to overwrite an existing receiver file.
- A separate CLI smoke test launched the actual one-shot TCP receiver, sent a bundle, and verified the saved bytes and acknowledgement.
- The Android-independent Java codec passes against the same Python golden frame in GitHub Actions.
- Android SDK 36 / JDK 17 compilation and lint pass in [verified CI run 39862708435](https://github.com/cmcintosh/FieldGuide/actions/runs/39862708435); a debug APK artifact was generated. Lint is a build gate, not a physical device test.
- Python 0.3.0 wheel packaging passes and includes the new link module/entry point. JavaScript syntax and local documentation links pass.
- No model weights, physical Android/Pi radios, phone UI, Bluetooth pairing, Wi-Fi Direct groups, hotspot behavior or speaker/microphone path have been exercised on real hardware here.
- No complete native Android LLM/maps application is claimed: the native app is a nearby-transfer companion with explicit file handoff.

Passing build/lint and byte-level tests does not establish a working physical link, device compatibility or LLM answer quality. The native app must be tested on two phones before publishing a supported-device claim. See the hardware-testing page and Android README.
