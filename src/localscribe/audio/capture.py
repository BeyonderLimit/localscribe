"""sounddevice-backed capture with ring buffer callback."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from .ring_buffer import RingBuffer


@dataclass
class AudioLevel:
    rms: float = 0.0
    peak: float = 0.0


class AudioCapture:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, ring_seconds: int = 30):
        self.sample_rate = sample_rate
        self.channels = channels
        self.ring = RingBuffer(sample_rate * ring_seconds * channels)
        self._stream: sd.InputStream | None = None
        self._level = AudioLevel()
        self._lock = threading.Lock()
        self._data_ready = threading.Event()

    def _callback(self, indata, frames, time, status) -> None:  # pragma: no cover - device callback
        # Hard rule: only append to the preallocated ring buffer and signal the worker.
        # No VAD, inference, disk I/O, or UI work may happen here.
        try:
            self.ring.write(indata)
        except Exception:
            pass
        self._data_ready.set()

    def start(self, device=None) -> None:
        if self._stream is not None:
            return
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._callback,
            device=device,
            blocksize=int(self.sample_rate * 0.02),
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    def level(self) -> AudioLevel:
        with self._lock:
            return AudioLevel(rms=self._level.rms, peak=self._level.peak)

    def has_data(self) -> bool:
        return self._data_ready.is_set()

    def read(self) -> np.ndarray:
        out = self.ring.read_available()
        if out.size:
            self._data_ready.clear()
            arr = out.astype(np.float64)
            with self._lock:
                self._level.rms = float(np.sqrt(np.mean(arr**2)))
                self._level.peak = float(np.max(np.abs(arr)))
        return out
