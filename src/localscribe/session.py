"""UI-agnostic session controller wiring capture, segmentation, and ASR.

Both the CLI (`localscribe run`) and the Textual app (`localscribe run --tui`)
drive this controller so the audio/engine lifecycle lives in one place.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np

from .audio.capture import AudioCapture
from .audio.segmenter import Segmenter
from .config import Config
from .engines.base import ASREngine, AudioChunk, EngineConfig
from .events import EventType, TranscriptEvent
from .platform import model_dir
from .storage.export import to_json, to_srt, to_txt
from .storage.transcript import TranscriptRecord, TranscriptStore

EventCallback = Callable[[TranscriptEvent], None]


def find_vosk_model_path(cfg: Config) -> Path | None:
    if cfg.model:
        p = Path(cfg.model)
        if p.exists():
            return p
    root = model_dir()
    for p in root.rglob("*"):
        if p.is_dir() and ((p / "am").exists() or (p / "graph").exists() or (p / "README").exists()):
            return p
    for p in root.iterdir():
        if p.is_dir():
            return p
    return None


def find_whisper_model_path(cfg: Config) -> Path | None:
    if cfg.model:
        p = Path(cfg.model)
        if p.exists():
            return p
    root = model_dir()
    for pattern in ("*.bin", "*.ggml"):
        for p in root.rglob(pattern):
            return p
    return None


def resolve_model_path(cfg: Config) -> Path | None:
    if cfg.engine == "whisper":
        return find_whisper_model_path(cfg)
    return find_vosk_model_path(cfg)


def build_engine(cfg: Config) -> ASREngine:
    if cfg.engine == "vosk":
        from .engines.vosk_engine import VoskEngine

        return VoskEngine()
    if cfg.engine == "whisper":
        from .engines.whisper_cpp import WhisperCppEngine

        return WhisperCppEngine()
    raise ValueError(f"unknown engine: {cfg.engine}")


class SessionController:
    """Owns the capture stream, ASR engine, and transcript store."""

    def __init__(
        self,
        cfg: Config,
        on_event: EventCallback | None = None,
        output: str | Path | None = None,
        capture: AudioCapture | None = None,
        engine: ASREngine | None = None,
    ):
        self.cfg = cfg
        self.on_event: EventCallback = on_event or (lambda ev: None)
        self.store = TranscriptStore(Path(output) if output else None)
        self.capture = capture or AudioCapture(
            sample_rate=cfg.sample_rate,
            channels=cfg.channels,
            ring_seconds=cfg.ring_buffer_seconds,
        )
        self.engine: ASREngine | None = engine
        self.segmenter: Segmenter | None = None
        self.model_path: Path | None = None
        self.paused = False
        self._stop = asyncio.Event()
        self._capture_task: asyncio.Task | None = None
        self._event_task: asyncio.Task | None = None
        self._stopped = False

    async def start(self) -> None:
        if self.engine is None:
            self.model_path = resolve_model_path(self.cfg)
            if self.model_path is None:
                if self.cfg.engine == "vosk":
                    raise RuntimeError(
                        "No Vosk model found. Run `localscribe models download vosk-small-en-us`."
                    )
                raise RuntimeError(
                    "No whisper.cpp model found. Set `model` in config to a .bin/.ggml file."
                )
            self.engine = build_engine(self.cfg)
        engine_cfg = EngineConfig(
            model_path=str(self.model_path) if self.model_path else None,
            sample_rate=self.cfg.sample_rate,
            threads=self.cfg.whisper_threads,
            language="en",
        )
        await self.engine.start(engine_cfg)
        if self.cfg.engine == "whisper":
            # whisper.cpp is not streaming: only completed VAD segments are sent.
            self.segmenter = Segmenter(
                sample_rate=self.cfg.sample_rate,
                frame_ms=self.cfg.frame_ms,
                pre_roll_ms=self.cfg.pre_roll_ms,
                post_roll_ms=self.cfg.post_roll_ms,
                max_segment_s=self.cfg.max_segment_s,
            )
        self._stop.clear()
        self.capture.start()
        self._capture_task = asyncio.create_task(self._capture_loop())
        self._event_task = asyncio.create_task(self._event_loop())

    async def _capture_loop(self) -> None:
        frame_s = self.cfg.frame_ms / 1000.0
        while not self._stop.is_set():
            await asyncio.sleep(0.0 if self.capture.has_data() else frame_s)
            if self._stop.is_set():
                break
            samples = self.capture.read()
            if samples.size == 0 or self.engine is None or self.paused:
                continue
            if self.segmenter is not None:
                for seg in self.segmenter.feed(samples):
                    await self._feed(seg.pcm)
            else:
                await self._feed(samples)

    async def _feed(self, samples: np.ndarray) -> None:
        if self.engine is None:
            return
        pcm = np.asarray(samples, dtype=np.int16).tobytes()
        await self.engine.feed(
            AudioChunk(pcm=pcm, sample_rate=self.cfg.sample_rate, channels=self.cfg.channels)
        )

    async def _event_loop(self) -> None:
        if self.engine is None:
            return
        # Runs until the engine's event stream ends (engine.stop() enqueues a sentinel),
        # so events flushed during shutdown are still persisted.
        async for ev in self.engine.events():
            if ev.type == EventType.FINAL:
                self.store.append(
                    TranscriptRecord(
                        type=ev.type.value,
                        text=ev.text,
                        start_s=ev.start_s,
                        end_s=ev.end_s,
                        metadata=ev.metadata,
                    )
                )
            self.on_event(ev)

    async def flush(self) -> None:
        """Finalize any in-progress audio so it is saved to the JSONL transcript."""
        if self.engine is not None:
            try:
                await self.engine.flush()
            except Exception:
                pass

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        return self.paused

    def add_marker(self, label: str = "") -> None:
        self.store.append(TranscriptRecord(type="marker", text=label))

    def export(self, out_path: str | Path | None = None) -> Path:
        records = self.store.read_all()
        if out_path is None:
            base = Path(self.cfg.export_dir).expanduser() if self.cfg.export_dir else Path.cwd()
            out_path = base / datetime.now().strftime("scribed-%m-%d-%Y-%H-%M.txt")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        to_txt(records, out_path)
        to_json(records, out_path.with_suffix(".json"))
        to_srt(records, out_path.with_suffix(".srt"))
        return out_path

    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._stop.set()
        # 1. Stop capturing new audio.
        if self._capture_task is not None:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except BaseException:
                pass
            self._capture_task = None
        # 2. Flush the segmenter and engine while the event loop is still draining,
        #    otherwise the final utterance would be dropped.
        if self.segmenter is not None and self.engine is not None:
            try:
                seg = self.segmenter.flush()
                if seg is not None:
                    await self._feed(seg.pcm)
            except Exception:
                pass
        if self.engine is not None:
            try:
                await self.engine.flush()
            except Exception:
                pass
            try:
                await self.engine.stop()
            except Exception:
                pass
        # 3. Let the event loop consume remaining events, then finish.
        if self._event_task is not None:
            try:
                await asyncio.wait_for(self._event_task, timeout=5.0)
            except BaseException:
                self._event_task.cancel()
                try:
                    await self._event_task
                except BaseException:
                    pass
            self._event_task = None
        self.capture.stop()
