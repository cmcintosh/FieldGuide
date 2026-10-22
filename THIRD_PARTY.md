# Licensing and external assets

FieldGuide's original project code and original example documents are GPL-2.0-only. The full license is in `LICENSE`; source files carry SPDX identifiers. The earlier standalone prototype was offered under MIT; this repository is the GPLv2 project requested by its owner.

The running Python application currently uses the standard library only. No Project NOMAD, llama.cpp, ggwave, MapLibre, model weights or geographic datasets are bundled here.

Optional external components retain their own licenses:

| Component | Relationship |
|---|---|
| llama.cpp / Ollama | Separately installed local inference server; communicate over loopback HTTP |
| Qwen and other models | User-installed assets; retain each model's license, provenance and checksum |
| Raster MBTiles maps | User-supplied content; preserve publisher attribution and redistribution terms |
| Reference documents | User-supplied content; source and declared license recorded but not verified |
| Project NOMAD | Feature reference only; no source or assets copied |
| ggwave | Research reference only; custom acoustic codec does not use its code or protocol |

GPLv2 for this application does not relicense independently supplied model weights, map data or documents. Review compatibility and notices before linking/bundling third-party libraries or distributing asset packs. In particular, do not assume Apache-2.0 NOMAD code can simply be relicensed as GPL-2.0-only. Maintain a component/license manifest when adding dependencies.

Upstream references: [GNU GPLv2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html), [GNU license compatibility list](https://www.gnu.org/licenses/license-list.html), [NOMAD](https://github.com/Crosstalk-Solutions/project-nomad), [llama.cpp](https://github.com/ggml-org/llama.cpp), [ggwave](https://github.com/ggerganov/ggwave).
