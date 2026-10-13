#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f CMakeLists.txt ]; then
  echo "Clone whisper.cpp into this directory first:" >&2
  echo "  git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git ." >&2
  exit 1
fi

cmake -S . -B build-cpu \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=ON

cmake --build build-cpu -j
