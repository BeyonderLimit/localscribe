"""Shared ASR engine protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from ..events import TranscriptEvent


@dataclass
class AudioChunk:
    pcm: bytes
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class EngineConfig:
    model_path: str | None = None
    sample_rate: int = 16000
    threads: int = 4
    language: str = "en"


class ASREngine(Protocol):
    async def start(self, config: EngineConfig) -> None: ...
    async def feed(self, chunk: AudioChunk) -> None: ...
    def events(self) -> AsyncIterator[TranscriptEvent]: ...
    async def flush(self) -> None: ...
    async def stop(self) -> None: ...
