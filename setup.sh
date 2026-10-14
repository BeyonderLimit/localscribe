#!/usr/bin/env bash
# LocalScribe system setup: build/install, probe hardware, run the config wizard.
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PYTHON="${PYTHON:-python3}"
BUILD_WHISPER=0
RUN_WIZARD=1
MODEL=""
EXPORT_DIR=""
WANT_MODEL=0
WANT_EXPORT=0

usage() {
  cat <<'EOF'
Usage: ./setup.sh [options]

  --model NAME     Download a model during setup (e.g. --model vosk-small-en-us)
  --export-dir DIR Directory for TXT/JSON/SRT exports (default: current directory)
  --whisper        Also build the optional whisper.cpp engine (needs a clone in native/whisper_cpp)
  --no-wizard      Skip the interactive configuration wizard
  -h, --help       Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      WANT_MODEL=1
      if [[ $# -ge 2 ]]; then MODEL="$2"; shift 2; else MODEL=""; shift; fi
      ;;
    --export-dir)
      WANT_EXPORT=1
      if [[ $# -ge 2 ]]; then EXPORT_DIR="$2"; shift 2; else EXPORT_DIR=""; shift; fi
      ;;
    --whisper) BUILD_WHISPER=1; shift ;;
    --no-wizard) RUN_WIZARD=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
if [[ "$WANT_MODEL" == 1 && ( -z "$MODEL" || "$MODEL" == --* ) ]]; then
  echo "Missing value for --model" >&2; usage; exit 2
fi
if [[ "$WANT_EXPORT" == 1 && ( -z "$EXPORT_DIR" || "$EXPORT_DIR" == --* ) ]]; then
  echo "Missing value for --export-dir" >&2; usage; exit 2
fi

echo "==> Checking Python ($PYTHON)"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.11+ and retry." >&2
  exit 1
fi
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    sys.exit("LocalScribe requires Python 3.11+ (found %d.%d)" % sys.version_info[:2])
PY

echo "==> Checking PortAudio system dependency"
if [[ "$(uname -s)" == "Linux" ]]; then
  if ! { ldconfig -p 2>/dev/null | grep -q libportaudio; }; then
    echo "PortAudio not found in the system loader. sounddevice wheels usually bundle it," >&2
    echo "but if audio capture fails, install it with:" >&2
    echo "  sudo apt-get install libportaudio2 portaudio19-dev   # Debian/Ubuntu" >&2
    echo "  sudo dnf install portaudio portaudio-devel           # Fedora" >&2
  fi
elif [[ "$(uname -s)" == "Darwin" ]]; then
  if ! brew list portaudio >/dev/null 2>&1; then
    echo "PortAudio not found via Homebrew. Install it with: brew install portaudio" >&2
  fi
fi

echo "==> Creating virtualenv ($VENV)"
if [[ ! -d "$VENV" ]]; then
  "$PYTHON" -m venv "$VENV"
fi
PIP="$VENV/bin/pip"
LOCALSCRIBE="$VENV/bin/localscribe"

echo "==> Installing LocalScribe (editable, with dev extras)"
"$PIP" install --upgrade pip
"$PIP" install -e ".[dev]"

if [[ "$BUILD_WHISPER" == "1" ]]; then
  echo "==> Building whisper.cpp (CPU-only)"
  if [[ -f native/whisper_cpp/CMakeLists.txt ]]; then
    bash native/whisper_cpp/build-cpu.sh
  else
    echo "native/whisper_cpp has no source; clone it first:" >&2
    echo "  git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git native/whisper_cpp" >&2
    echo "Skipping whisper.cpp build." >&2
  fi
fi

echo "==> Probing hardware"
"$LOCALSCRIBE" probe

if [[ -n "$EXPORT_DIR" ]]; then
  echo "==> Setting export directory to $EXPORT_DIR"
  "$VENV/bin/python" - "$EXPORT_DIR" <<'PY'
import sys

from localscribe.config import Config

cfg = Config.load()
cfg.export_dir = sys.argv[1]
cfg.save()
PY
fi

if [[ -n "$MODEL" ]]; then
  echo "==> Downloading model: $MODEL"
  "$LOCALSCRIBE" models download "$MODEL"
fi

if [[ "$RUN_WIZARD" == "1" ]]; then
  echo "==> Starting configuration wizard"
  "$LOCALSCRIBE" setup
fi

echo
echo "Setup complete. Next steps:"
if [[ -z "$MODEL" ]]; then
  echo "  $LOCALSCRIBE models download vosk-small-en-us"
fi
echo "  $LOCALSCRIBE run --tui"
