"""whisper.cpp segment-transcription adapter (CPU only)."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from ..events import EventType, TranscriptEvent
from .base import AudioChunk, EngineConfig


class WhisperCppEngine:
    def __init__(self):
        self._cfg: EngineConfig | None = None
        self._binary: str | None = None
        self._queue: asyncio.Queue[TranscriptEvent | None] | None = None

    async def start(self, config: EngineConfig) -> None:
        self._cfg = config
        self._binary = self._find_binary()
        if self._binary is None:
            raise RuntimeError("whisper.cpp binary not found; build native/whisper_cpp/build-cpu")
        if not config.model_path or not Path(config.model_path).exists():
            raise ValueError("model_path is required and must exist for whisper.cpp")
        self._queue = asyncio.Queue()

    def _find_binary(self) -> str | None:
        env = os.environ.get("WHISPER_CPP_BINARY")
        if env and Path(env).exists():
            return env
        for name in ("whisper-cli", "whisper-cpp", "main"):
            found = shutil.which(name)
            if found:
                return found
        # repo-local
        candidates = [
            Path("native/whisper_cpp/build-cpu/bin/whisper-cli"),
            Path("native/whisper_cpp/build-cpu/whisper-cli"),
            Path("native/whisper_cpp/build/bin/main"),
            Path("native/whisper_cpp/build/main"),
        ]
        for c in candidates:
            if c.exists():
                return str(c.resolve())
        return None

    async def feed(self, chunk: AudioChunk) -> None:
        # whisper.cpp runs per segment, not streaming. Caller should pass segments.
        await self.transcribe(chunk)

    async def transcribe(self, chunk: AudioChunk) -> None:
        if self._cfg is None or self._binary is None or self._queue is None:
            raise RuntimeError("engine not started")
        loop = asyncio.get_event_loop()
        ev = await loop.run_in_executor(None, lambda: self._run(chunk))
        if ev is not None:
            await self._queue.put(ev)

    def _run(self, chunk: AudioChunk) -> TranscriptEvent | None:
        cfg = self._cfg
        assert cfg is not None and self._binary is not None
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "segment.wav"
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(chunk.channels)
                w.setsampwidth(2)
                w.setframerate(chunk.sample_rate)
                w.writeframes(chunk.pcm if isinstance(chunk.pcm, (bytes, bytearray)) else bytes(chunk.pcm))
            cmd = [
                self._binary,
                "-m",
                str(cfg.model_path),
                "-f",
                str(wav),
                "-l",
                cfg.language if hasattr(cfg, "language") else "en",
                "-t",
                str(cfg.threads),
                "-nt",
                "-np",
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            except Exception as e:
                return TranscriptEvent(type=EventType.ENGINE_WARNING, text=f"whisper.cpp failed: {e}")
            text = self._parse(proc.stdout or "")
            if not text.strip():
                # fallback stderr
                text = self._parse(proc.stderr or "")
            text = text.strip()
            if not text:
                return None
            return TranscriptEvent(type=EventType.FINAL, text=text)

    @staticmethod
    def _parse(output: str) -> str:
        lines = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            # strip leading timestamp brackets
            m = re.sub(r"^\[[^\]]*\]\s*", "", line)
            lines.append(m)
        return " ".join(lines)

    async def flush(self) -> None:
        # no-op: segment engine
        pass

    def events(self):
        async def gen():
            assert self._queue is not None
            while True:
                item = await self._queue.get()
                if item is None:
                    break
                yield item

        return gen()

    async def stop(self) -> None:
        if self._queue is not None:
            await self._queue.put(None)
        self._binary = None
