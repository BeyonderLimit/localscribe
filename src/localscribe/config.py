"""User configuration and defaults."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .platform import data_dir


@dataclass
class Config:
    sample_rate: int = 16000
    channels: int = 1
    frame_ms: int = 30
    pre_roll_ms: int = 300
    post_roll_ms: int = 500
    max_segment_s: int = 20
    ring_buffer_seconds: int = 30
    model: str | None = None
    engine: str = "vosk"
    whisper_threads: int = 4
    ui_refresh_ms: int = 100
    retention: str = "keep"  # keep | hours:N | delete
    export_dir: str | None = None  # where TXT/JSON/SRT exports go; None = cwd
    verbose: bool = False

    def path(self) -> Path:
        return data_dir() / "config.json"

    def save(self) -> None:
        self.path().write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> Config:
        p = data_dir() / "config.json"
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text())
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()
