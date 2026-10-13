# LocalScribe 0.1.1

Offline, hardware-adaptive ASR dictation TUI (v0.1: CPU-only, Vosk default).

## Versioning

Version is stored in `pyproject.toml` and `src/localscribe/__init__.py`.
Use:

```bash
localscribe --version
localscribe version
```

## Setup

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

Press Ctrl+C to stop a session; transcript JSONL is saved under the data directory
and a readable `.txt` export is written to the current directory as
`scribed-<mm-dd-yyyy-hh-mm>.txt`.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
```
