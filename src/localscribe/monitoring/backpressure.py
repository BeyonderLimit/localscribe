"""Backpressure policy helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackpressureState:
    queue_depth: int
    queue_capacity: int

    @property
    def ratio(self) -> float:
        if self.queue_capacity <= 0:
            return 0.0
        return self.queue_depth / self.queue_capacity

    def level(self) -> str:
        r = self.ratio
        if r < 0.5:
            return "ok"
        if r < 0.75:
            return "warn"
        if r < 0.9:
            return "pressure"
        return "critical"

    @staticmethod
    def policy_steps() -> list[str]:
        return [
            "increase VAD post-roll slightly",
            "reduce Whisper overlap",
            "reduce UI refresh frequency",
            "enable disk spooling",
            "warn user and suggest smaller model",
            "lossy mode only if user approves",
        ]
