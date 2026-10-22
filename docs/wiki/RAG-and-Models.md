# RAG and models

RAG is the main AI design: retrieve relevant local text, provide a few excerpts to a compact model and show source links. The preview uses SQLite FTS5/BM25 without an embedding server. There is no silent cloud fallback. Model URLs are restricted to numeric loopback HTTP addresses; proxies and redirects are disabled. A separately installed server must itself use local model weights.

Compare quantized post-trained Qwen3.5-2B and 0.8B models on actual devices. The first is a quality candidate; the second is a lower-memory candidate. Neither is validated here. Use a compatible llama.cpp build and record the GGUF hash/runtime version. A default Ollama tag may have different precision/vision assets than a small text-only Q4 conversion.

The current prompt includes up to four excerpts, uses an approximate character budget and reserves 512 output tokens. It is not tokenizer-aware. Search remains available if the model fails. Citation checks only verify that identifiers exist; they do not prove factual support. Retrieved content is untrusted data, and prompt instructions are not a complete defense against malicious documents.

Planned hybrid search adds a small local embedding model plus topic shards prepared ahead of time. Queries must use the same embedder and normalization as document vectors. Keep large Wikipedia collections compressed with ZIM/libzim search rather than embedding the entire encyclopedia for the initial phone release. Direct ZIM/PDF support is not present yet.

Inventory calculations and map operations remain deterministic typed tools; the model must not invent quantities, execute arbitrary commands, or make edits on the user's behalf.
