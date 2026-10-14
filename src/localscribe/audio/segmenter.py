"""VAD-gated speech segmentation with pre/post-roll and max duration."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from .vad import VAD


@dataclass
class AudioSegment:
    pcm: np.ndarray
    start_s: float
    end_s: float


class Segmenter:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        pre_roll_ms: int = 300,
        post_roll_ms: int = 500,
        max_segment_s: int = 20,
        vad: VAD | None = None,
    ):
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.pre_roll_ms = pre_roll_ms
        self.post_roll_ms = post_roll_ms
        self.max_segment_s = max_segment_s
        self.vad: VAD
        if vad is None:
            from .vad import EnergyVAD

            self.vad = EnergyVAD()
        else:
            self.vad = vad
        self.frame_size = sample_rate * frame_ms // 1000
        self.pre_roll_frames = max(1, pre_roll_ms // frame_ms)
        self.post_roll_samples = sample_rate * post_roll_ms // 1000
        self.max_segment_samples = sample_rate * max_segment_s

        self._pre_roll: deque[np.ndarray] = deque(maxlen=self.pre_roll_frames)
        self._segment: list[np.ndarray] = []
        self._in_speech = False
        self._silence_run = 0
        self._total = 0  # samples consumed
        self._seg_start = 0.0

    def _finalize(self) -> AudioSegment | None:
        if not self._segment:
            self._in_speech = False
            self._silence_run = 0
            self._pre_roll.clear()
            return None
        pcm = np.concatenate(self._segment).astype(np.int16, copy=False)
        start = self._seg_start
        end = self._total / self.sample_rate
        self._segment = []
        self._in_speech = False
        self._silence_run = 0
        self._pre_roll.clear()
        return AudioSegment(pcm=pcm, start_s=start, end_s=end)

    def feed(self, samples: np.ndarray) -> list[AudioSegment]:
        arr = np.asarray(samples).reshape(-1).astype(np.int16, copy=False)
        out: list[AudioSegment] = []
        i = 0
        n = arr.shape[0]
        while i + self.frame_size <= n:
            frame = arr[i : i + self.frame_size]
            speech = self.vad.is_speech(frame)
            # update pre-roll with current frame before decisions
            self._pre_roll.append(frame.copy())
            if not self._in_speech:
                if speech:
                    self._in_speech = True
                    self._seg_start = (self._total + i) / self.sample_rate - (len(self._pre_roll) - 1) * self.frame_ms / 1000.0
                    if self._seg_start < 0:
                        self._seg_start = 0.0
                    # include pre-roll (all queued frames)
                    self._segment = [f.copy() for f in self._pre_roll]
                    self._silence_run = 0
            else:
                self._segment.append(frame.copy())
                if speech:
                    self._silence_run = 0
                else:
                    self._silence_run += self.frame_size
                seg_len = sum(f.shape[0] for f in self._segment)
                if self._silence_run >= self.post_roll_samples or seg_len >= self.max_segment_samples:
                    seg = self._finalize()
                    if seg is not None:
                        out.append(seg)
            i += self.frame_size
        self._total += n
        return out

    def flush(self) -> AudioSegment | None:
        return self._finalize()
