# Validation — 22 October 2026

- Python 3.12 / SQLite FTS5: 43 automated tests pass.
- Tests cover storage/import/backup, live local HTTP and model-client fixture behavior, raster MBTiles row conversion/read-only access, selected peer transfer between independent databases, repeated import, invalid/expired codes and integrity failure.
- Audio tests cover both generated profiles, UTF-8 budgets, synthetic noise, sample offset, truncation and CRC rejection.
- Editable installation and wheel build pass; the wheel includes all local UI assets and the GPL license. Source and installed audio CLI commands pass.
- JavaScript syntax is checked; live DOM rendering was not verified because no local Chromium executable is installed.
- No model weights, native Android APK, Pi/phone hardware, actual Wi-Fi/Bluetooth radios or speaker/microphone path were tested.
- GitHub Actions is configured for Python 3.10, 3.12 and 3.13. Local passing tests do not imply that remote CI has completed.

The model endpoint fixture does not establish inference quality. Generated-WAV round trips do not establish an acoustic link. See the hardware testing wiki page for required next measurements.
