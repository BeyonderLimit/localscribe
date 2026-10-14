"""Vosk streaming engine adapter."""

from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    import vosk
except Exception:  # pragma: no cover
    vosk = None

from ..events import EventType, TranscriptEvent
from .base import AudioChunk, EngineConfig


class VoskEngine:
    def __init__(self):
        self._model: Any = None
        self._rec: Any = None
        self._cfg: EngineConfig | None = None
        self._queue: asyncio.Queue[TranscriptEvent | None] | None = None

    async def start(self, config: EngineConfig) -> None:
        if vosk is None:
            raise RuntimeError("vosk is not installed")
        if not config.model_path:
            raise ValueError("model_path is required for Vosk")
        self._cfg = config
        # Construct in executor to avoid blocking.
        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(None, lambda: vosk.Model(config.model_path))
        self._rec = await loop.run_in_executor(
            None, lambda: vosk.KaldiRecognizer(self._model, config.sample_rate)
        )
        self._queue = asyncio.Queue()

    async def feed(self, chunk: AudioChunk) -> None:
        if self._rec is None or self._queue is None:
            raise RuntimeError("engine not started")
        loop = asyncio.get_event_loop()
        data = chunk.pcm
        result_json = await loop.run_in_executor(None, lambda: self._handle(data))
        if result_json:
            await self._queue.put(result_json)

    def _handle(self, data: bytes) -> TranscriptEvent | None:
        if self._rec.AcceptWaveform(data):
            res = json.loads(self._rec.Result())
            text = (res.get("text") or "").strip()
            if not text:
                return None
            return TranscriptEvent(
                type=EventType.FINAL,
                text=text,
                start_s=res.get("result", [{}])[0].get("start") if res.get("result") else None,
                end_s=res.get("result", [{}])[-1].get("end") if res.get("result") else None,
            )
        else:
            res = json.loads(self._rec.PartialResult())
            text = (res.get("partial") or "").strip()
            if not text:
                return None
            return TranscriptEvent(type=EventType.PARTIAL, text=text)

    async def flush(self) -> None:
        if self._rec is None or self._queue is None:
            return
        loop = asyncio.get_event_loop()
        ev = await loop.run_in_executor(None, self._finalize)
        if ev is not None:
            await self._queue.put(ev)

    def _finalize(self) -> TranscriptEvent | None:
        res = json.loads(self._rec.FinalResult())
        text = (res.get("text") or "").strip()
        if not text:
            return None
        return TranscriptEvent(type=EventType.FINAL, text=text)

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
        self._rec = None
        self._model = None
