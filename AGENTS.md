# LocalScribe

Scaffolded implementation exists under src/localscribe with tests and pyproject.toml. Use the local venv: `.venv/bin/pip install -e ".[dev]"`; PortAudio system library required for capture.

## Source of truth

- `localscribe-architecture.md` is authoritative for v0.1 decisions, especially its "Revised v0.1 scope" and "Trimmed project structure".
- `localscribe.md` is the broader long-term vision and contains superseded scope (GPU detection, broader feature set). Resolve conflicts in favor of `localscribe-architecture.md`.

## v0.1 scope (deliberately narrow)

- Linux + macOS, English first, CPU-only inference
- Vosk streaming engine as default; whisper.cpp as optional quality engine
- 16 kHz mono PCM capture, VAD-gated segmentation
- Incremental JSONL transcript autosave, Textual TUI, TXT/SRT/JSON export
- Local model manager with checksum verification
- No GPU detection/backend logic, no automatic engine or model switching during a session

## Non-negotiable invariants

- Audio callback (PortAudio/sounddevice) may only append to the preallocated ring buffer and signal the worker. Never VAD, inference, disk I/O, or Textual updates in the callback.
- Internal audio format: 16 kHz / mono / 16-bit PCM; 20-30 ms VAD frames; 250-500 ms pre-roll; 300-800 ms post-roll; 15-30 s max segment; bounded queue with optional disk spool.
- Vosk is true streaming (feed PCM continuously; partial/final via AcceptWaveform/PartialResult/Result).
- whisper.cpp receives only completed VAD segments, never naive rolling windows; reconcile overlaps via timestamps/token alignment.
- whisper.cpp build must stay CPU-only: plain Release CMake, no CUDA/Metal/Core ML/Vulkan/OpenCL/BLAS flags. Build script native/whisper_cpp/build-cpu.sh.
- Engines share one async ASREngine protocol (start, feed, events, flush, stop) with typed events (PartialTranscript, FinalSegment, EngineWarning, BacklogWarning, ResourceRecommendation).
- Never silently drop speech. Backpressure order: increase VAD post-roll -> reduce Whisper overlap -> reduce UI refresh -> enable disk spool -> warn user/suggest smaller model -> lossy mode only if user approves.
- ASR eligibility: sustained RTF <= 0.6 with stable memory and no persistent backlog. Never select a model solely because it fits in RAM.

## Model manager rules

- Catalog entries: engine, language, license, URL, SHA-256, size, minimum RAM, supported backend.
- Download to <model>.part, verify checksum, atomically rename; keep manifest.json (source, version, checksum, install date, license).
- Never network access during an active dictation session. CLI: localscribe models download|list|verify.

## Toolchain (when implemented)

Python 3.11+, uv, Textual, sounddevice+NumPy, Vosk, whisper.cpp, pytest+pytest-asyncio, ruff, mypy. Target layout and implementation order are in localscribe-architecture.md.
## Commands
- tests: `.venv/bin/python -m pytest -q`
- lint: `.venv/bin/ruff check src tests`
- typecheck: `.venv/bin/mypy src`
- run session: `.venv/bin/localscribe run`
- TUI only: `.venv/bin/localscribe run --tui`
- models: `.venv/bin/localscribe models list|download <name>|verify`
