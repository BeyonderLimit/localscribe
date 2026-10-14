# LocalScribe

Offline, CPU-only ASR dictation TUI (Linux + macOS, English). The scaffold is now
wired end-to-end: `run` and `run --tui` drive `src/localscribe/session.py::SessionController`.

## Setup

- venv + install: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`, or run `./setup.sh`
  (venv + install + `probe` + config wizard; `--whisper` also builds whisper.cpp, `--no-wizard` skips).
- System dep: PortAudio (`sudo apt-get install libportaudio2 portaudio19-dev`).
- Version is duplicated in `pyproject.toml` and `src/localscribe/__init__.py`; keep them in sync.

## Commands

- tests: `.venv/bin/python -m pytest -q`
- single test: `.venv/bin/python -m pytest tests/test_session.py::test_build_engine_by_name`
- lint: `.venv/bin/ruff check src tests` (line-length 100, rules E/F/I/UP)
- typecheck: `.venv/bin/mypy src`
- run: `.venv/bin/localscribe run` | TUI: `.venv/bin/localscribe run --tui`
- run flags: `--engine vosk|whisper`, `--output <jsonl path>`
- inspect: `localscribe probe | config | config --wizard | setup | version`
- models: `localscribe models list | download <name> | verify`

## Source of truth

- `localscribe.md` is the design doc; it contains long-term GPU/backend vision, but v0.1 is
  CPU-only and narrower. README + code win on conflicts.
- There is no `localscribe-architecture.md` (older notes cited it); do not recreate/reference it.

## Wiring / architecture

- `SessionController` (`session.py`) owns capture + engine + transcript store for both CLI and
  TUI. Extend it rather than duplicating lifecycle code in `cli.py` or the TUI.
- CLI prints events and exports TXT/JSON/SRT on exit; the Textual app drives the same controller
  (exports on exit and Ctrl+E, Ctrl+S flushes the in-progress utterance to JSONL) and updates
  widgets from a timer (events are queued, not touched from the ASR task). Exports go to `cfg.export_dir`
  (default CWD); the JSONL autosave always goes to the transcript store.
- Engine protocol: `engines/base.py::ASREngine` (start/feed/events/flush/stop); typed events in
  `events.py` (`EventType`). Any new engine must implement this protocol.
- Vosk consumes raw captured PCM continuously (true streaming). whisper.cpp receives only completed
  VAD `Segmenter` segments, never naive rolling windows.
- whisper.cpp needs `cfg.model` to point at a `.bin`/`.ggml` file and a built binary, found via
  `WHISPER_CPP_BINARY` or `native/whisper_cpp/build-cpu/...` (build with `native/whisper_cpp/build-cpu.sh`,
  plain Release CMake, CPU-only — no CUDA/Metal/Vulkan/OpenCL/BLAS flags).
- Paths live only in `platform.py`: data dir `~/.local/share/localscribe` (macOS
  `~/Library/Application Support/LocalScribe`), models `models/<engine>/<name>/...`,
  transcripts `transcripts/session.jsonl`, config `config.json`.

## Invariants (do not break)

- The PortAudio callback (`audio/capture.py::_callback`) may ONLY write to the preallocated ring
  buffer and set the data-ready event. RMS/level is computed in `read()` on the worker thread.
  Never VAD, inference, disk I/O, or UI work in the callback.
- Internal audio format: 16 kHz / mono / int16; VAD frames 20-30 ms; pre-roll 250-500 ms;
  post-roll 300-800 ms; max segment 15-30 s; bounded ring buffer.
- Never silently drop speech. Backpressure escalation order is
  `monitoring/backpressure.py::policy_steps`.
- ASR eligibility is sustained RTF <= 0.6 with stable memory (`hardware/benchmark.py`); never select
  a model solely because it fits in RAM.
- Optional WebRTC VAD (`webrtcvad`) is used only if installed; otherwise `EnergyVAD` is used.

## Model manager

- `models/catalog.py` entries carry engine, language, license, URL, SHA-256, size, min RAM, backend.
- Download writes `<model>.part`, verifies SHA-256, atomically renames, extracts zips, and records
  `manifest.json`; the HTTP client is `requests` (declared in `pyproject.toml`).
- No network access during a live dictation session.
- Limitation: `models verify` currently only checks that installed paths exist; verify does not
  re-hash files yet.

## Toolchain

Python 3.11+, Textual, sounddevice + NumPy, Vosk (default), whisper.cpp (optional),
pytest + pytest-asyncio, ruff, mypy.
