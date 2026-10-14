"""Incremental JSONL transcript storage with recovery."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..platform import transcript_dir


@dataclass
class TranscriptRecord:
    type: str
    text: str
    start_s: float | None = None
    end_s: float | None = None
    metadata: dict[str, Any] | None = None


class TranscriptStore:
    def __init__(self, path: Path | None = None):
        if path is None:
            path = transcript_dir() / "session.jsonl"
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: TranscriptRecord) -> None:
        line = json.dumps(asdict(record)) + "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def read_all(self) -> list[TranscriptRecord]:
        if not self.path.exists():
            return []
        out: list[TranscriptRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                out.append(TranscriptRecord(**data))
            except Exception:
                continue
        return out

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
