# LocalScribe 0.1.2

Offline, hardware-adaptive ASR dictation TUI (v0.1: CPU-only, Vosk default).

## Versioning

Version is stored in `pyproject.toml` and `src/localscribe/__init__.py`.
Use:

```bash
localscribe --version
localscribe version
```

## Setup

Quick start (venv + install + hardware probe + config wizard):

```bash
./setup.sh
# options:
#   --model vosk-small-en-us   download a model during setup
#   --export-dir ~/transcripts keep TXT/JSON/SRT exports out of the source tree
#   --whisper                  also build the optional whisper.cpp engine
#   --no-wizard                skip the interactive wizard
```

Manual setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

System dependency: PortAudio (e.g. `sudo apt-get install libportaudio2 portaudio19-dev`).

Create a global command (optional):

```bash
sudo ln -sf /path/to/localscribe/.venv/bin/localscribe /usr/local/bin/localscribe
```

## Usage

```bash
localscribe probe
localscribe models list
localscribe models download vosk-small-en-us
localscribe models verify
localscribe config
localscribe setup
localscribe run
localscribe run --tui
```

`run` accepts `--engine vosk|whisper` and `--output <jsonl path>`.

## Transcripts

Output is saved in two forms:

- **Autosave (JSONL)** — every finalized segment (and each marker) is appended and `fsync`ed
  to `<data-dir>/transcripts/session.jsonl`, or to `--output <path>`. This happens live as you
  speak; `<data-dir>` is `~/.local/share/localscribe` on Linux (`$XDG_DATA_HOME/localscribe`
  if set) and `~/Library/Application Support/LocalScribe` on macOS.
- **Exports (TXT/JSON/SRT)** — `scribed-<mm-dd-yyyy-hh-mm>.txt`, `.json`, and `.srt`. They are
  written to the current directory by default, or to `export_dir` if set in `config.json`
  (`localscribe setup` prompts for it; `setup.sh --export-dir DIR` sets it non-interactively).

When exports happen:

- CLI (`localscribe run`): automatically on exit (Ctrl+C).
- TUI (`--tui`): on exit (Esc) and when you press `Ctrl+E`. `Ctrl+S` finalizes the in-progress
  utterance into the JSONL autosave; `Ctrl+M` inserts a marker.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
```
