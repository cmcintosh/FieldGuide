# Contributing

Contributions to FieldGuide are accepted under GPL-2.0-only. Preserve copyright and license notices. Do not copy code with incompatible terms; keep external model/content licenses separate.

Use a focused branch and pull request. Explain the user-visible behavior, run relevant tests, and identify device-specific work that has not been exercised. Tests belong in `tests`; production code belongs in `src/fieldguide`.

Keep the core usable without internet or a model. Do not add CDN assets, silent cloud fallback, automatic execution of imported material, or automatic transmission of private records. New transports must be user-initiated and must not claim encryption, authentication, reliability or hardware compatibility that they have not implemented and tested.

Add meaningful regression tests for database migrations, pack formats, network boundaries and transport codecs. Document protocol changes and compatibility. For hardware changes, record the exact device, OS, sample rate/model hash and reproduction steps.

Before submitting, run the commands in README. Never commit personal databases, recordings, map/model files or credentials. Keep `docs/wiki`, architecture and feature status current with the implementation.
